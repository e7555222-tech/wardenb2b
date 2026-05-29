from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import get_db, init_db
from models import User, Lead, Subscription, TierEnum, SubscriptionStatus
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Admin kontrolü
def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Warden B2B API")
app.state.limiter = limiter

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da spesifik domain'ler kullanılmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return HTTPException(
        status_code=429,
        detail="Rate limit exceeded. Too many requests."
    )

# Pydantic modelleri
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    company: Optional[str]
    is_admin: bool
    
    class Config:
        from_attributes = True

class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    budget: float

class LeadResponse(BaseModel):
    id: int
    name: str
    email: str
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    budget: float
    score: Optional[int] = None
    sentiment: Optional[str] = None
    action: Optional[str] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    # Email kontrolü
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Yeni kullanıcı oluştur
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        password_hash=hashed_password,
        name=user.name,
        company=user.company
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Varsayılan subscription oluştur
    subscription = Subscription(
        user_id=new_user.id,
        tier=TierEnum.FREE,
        status=SubscriptionStatus.ACTIVE
    )
    db.add(subscription)
    db.commit()
    
    return new_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.put("/users/me")
def update_user_profile(
    name: Optional[str] = None,
    company: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if name:
        current_user.name = name
    if company is not None:
        current_user.company = company
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.post("/leads", response_model=LeadResponse)
def create_lead(lead: LeadCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Subscription kontrolü
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription"
        )
    
    # Lead limit kontrolü (Free tier: 10 lead)
    if subscription.tier == TierEnum.FREE:
        lead_count = db.query(Lead).filter(Lead.user_id == current_user.id).count()
        if lead_count >= 10:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Free tier limit reached (10 leads). Upgrade to Pro."
            )
    
    new_lead = Lead(
        user_id=current_user.id,
        name=lead.name,
        email=lead.email,
        company_url=lead.company_url,
        budget=lead.budget
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    return new_lead

@app.get("/leads", response_model=List[LeadResponse])
def get_leads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.user_id == current_user.id).order_by(Lead.created_at.desc()).all()
    return leads

@app.get("/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.put("/leads/{lead_id}/score")
def update_lead_score(
    lead_id: int,
    score: int,
    sentiment: str,
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.user_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.score = score
    lead.sentiment = sentiment
    lead.action = action
    db.commit()
    db.refresh(lead)
    
    return lead

# n8n webhook endpoint'i (authentication gerektirmez)
@app.post("/webhook/lead-score")
def webhook_update_lead_score(
    lead_id: int,
    score: int,
    sentiment: str,
    action: str,
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.score = score
    lead.sentiment = sentiment
    lead.action = action
    db.commit()
    db.refresh(lead)
    
    return {"status": "success", "lead_id": lead_id}

@app.get("/subscription")
def get_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription

# Admin endpoint'leri
@app.get("/admin/users")
def get_all_users(admin_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users

@app.get("/admin/leads")
def get_all_leads(admin_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return leads

@app.put("/admin/users/{user_id}/make-admin")
def make_user_admin(
    user_id: int,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_admin = True
    db.commit()
    db.refresh(user)
    
    return user

@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"status": "success", "message": "User deleted"}

# Password reset endpoint'leri
@app.post("/password-reset/request")
def request_password_reset(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Güvenlik için kullanıcı bulunsa da bulunmasa da aynı mesajı döndür
        return {"message": "Eğer bu e-posta kayıtlıysa, reset linki gönderildi"}
    
    # Reset token oluştur
    reset_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # Gerçek uygulamada email gönderilir, şimdilik token'ı döndür
    return {
        "message": "Reset token oluşturuldu (gerçek uygulamada email gönderilir)",
        "reset_token": reset_token  # Test için
    }

@app.post("/password-reset/confirm")
def confirm_password_reset(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.reset_token != token or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Şifre başarıyla değiştirildi"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
