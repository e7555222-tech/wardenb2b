import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from database import SessionLocal, get_db, init_db
from models import Lead, Subscription, SubscriptionStatus, TierEnum, User
from tier_limits import tier_lead_limit

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
DEMO_SEED = os.getenv("DEMO_SEED", "false").lower() == "true"

_DEMO_EMAIL = "demo@warden.app"
_DEMO_PASSWORD = "Demo1234!"


def _seed_admin() -> None:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if existing:
            if not existing.is_admin:
                existing.is_admin = True
                db.commit()
            return
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            name=ADMIN_NAME,
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        db.add(Subscription(user_id=admin.id, tier=TierEnum.ENTERPRISE, status=SubscriptionStatus.ACTIVE))
        db.commit()
    finally:
        db.close()


def _seed_demo() -> None:
    if not DEMO_SEED:
        return
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == _DEMO_EMAIL).first():
            return
        demo_user = User(
            email=_DEMO_EMAIL,
            password_hash=get_password_hash(_DEMO_PASSWORD),
            name="Demo Kullanıcı",
            company="Warden Demo A.Ş.",
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        db.add(Subscription(user_id=demo_user.id, tier=TierEnum.PRO, status=SubscriptionStatus.ACTIVE))
        db.commit()
        demo_leads = [
            Lead(user_id=demo_user.id, name="Ahmet Yılmaz", email="ahmet@techstartup.com",
                 company_name="TechStartup A.Ş.", company_url="techstartup.com",
                 budget=20000, score=92, sentiment="Yüksek", action="Hemen aranmalı"),
            Lead(user_id=demo_user.id, name="Selin Kaya", email="selin@dijitalajans.com",
                 company_name="Dijital Ajans B", company_url="dijitalajans.com",
                 budget=8000, score=71, sentiment="Orta", action="Bu hafta takip et"),
            Lead(user_id=demo_user.id, name="Mehmet Demir", email="mehmet@uretim.com",
                 company_name="Üretim Firması C", company_url=None,
                 budget=35000, score=85, sentiment="Yüksek", action="Demo planla"),
            Lead(user_id=demo_user.id, name="Ayşe Çelik", email="ayse@lojistik.com",
                 company_name="Lojistik D Ltd.", company_url="lojistikd.com",
                 budget=5000, score=42, sentiment="Düşük", action="Bekle - bütçe yetersiz"),
            Lead(user_id=demo_user.id, name="Can Öztürk", email="can@fintech.io",
                 company_name="FinTech E", company_url="fintech-e.io",
                 budget=50000, score=97, sentiment="Yüksek", action="Aynı gün ara - öncelikli!"),
        ]
        db.add_all(demo_leads)
        db.commit()
    finally:
        db.close()


def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def enforce_lead_limit(user_id: int, subscription: Subscription, db: Session) -> None:
    limit = tier_lead_limit(subscription.tier)
    if limit is None:
        return
    lead_count = db.query(Lead).filter(Lead.user_id == user_id).count()
    if lead_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"{subscription.tier.value} tier limit reached ({limit} leads). "
                "Upgrade your plan."
            ),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_admin()
    _seed_demo()
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Warden B2B API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Too many requests."})


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    company: Optional[str]
    is_admin: bool
    created_at: Optional[datetime] = None

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
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class LeadScoreWebhook(BaseModel):
    lead_id: int
    score: int
    sentiment: str
    action: str


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        name=user.name,
        company=user.company,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    subscription = Subscription(user_id=new_user.id, tier=TierEnum.FREE, status=SubscriptionStatus.ACTIVE)
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

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.put("/users/me", response_model=UserResponse)
def update_user_profile(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        current_user.name = body.name
    if body.company is not None:
        current_user.company = body.company

    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/users/me/change-password")
def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.reset_token = None
    current_user.reset_token_expires = None
    db.commit()
    return {"message": "Password updated successfully"}


@app.post("/leads", response_model=LeadResponse)
def create_lead(
    lead: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active subscription")

    enforce_lead_limit(current_user.id, subscription, db)

    new_lead = Lead(
        user_id=current_user.id,
        name=lead.name,
        email=lead.email,
        company_name=lead.company_name,
        company_url=lead.company_url,
        budget=lead.budget,
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return new_lead


@app.get("/leads", response_model=List[LeadResponse])
def get_leads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Lead).filter(Lead.user_id == current_user.id).order_by(Lead.created_at.desc()).all()


@app.get("/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.put("/leads/{lead_id}/score", response_model=LeadResponse)
def update_lead_score(
    lead_id: int,
    score: int,
    sentiment: str,
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.score = score
    lead.sentiment = sentiment
    lead.action = action
    db.commit()
    db.refresh(lead)
    return lead


@app.post("/webhook/lead-score")
def webhook_update_lead_score(
    payload: LeadScoreWebhook,
    x_webhook_secret: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.score = payload.score
    lead.sentiment = payload.sentiment
    lead.action = payload.action
    db.commit()
    db.refresh(lead)

    return {"status": "success", "lead_id": payload.lead_id}


@app.get("/subscription")
def get_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {
        "tier": subscription.tier.value,
        "status": subscription.status.value,
        "lead_limit": tier_lead_limit(subscription.tier),
    }


@app.get("/admin/users", response_model=List[UserResponse])
def get_all_users(admin_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@app.get("/admin/leads", response_model=List[LeadResponse])
def get_all_leads(admin_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


@app.put("/admin/users/{user_id}/make-admin", response_model=UserResponse)
def make_user_admin(user_id: int, admin_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    db.commit()
    db.refresh(user)
    return user


@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, admin_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "success", "message": "User deleted"}


@app.post("/password-reset/request")
def request_password_reset(body: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        return {"message": "If this email is registered, a reset link was sent"}

    reset_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    return {
        "message": "Reset token created (email delivery not configured)",
        "reset_token": reset_token,
    }


@app.post("/password-reset/confirm")
def confirm_password_reset(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.reset_token != body.token or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user.password_hash = get_password_hash(body.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password updated successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
