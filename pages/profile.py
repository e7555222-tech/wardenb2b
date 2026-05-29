import streamlit as st
import requests

st.set_page_config(page_title="Warden B2B - Profil", page_icon="🛡️", layout="centered")

API_URL = "http://localhost:8000"

# Login kontrolü
if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

# Sidebar
with st.sidebar:
    st.markdown(f"### 👋 {st.session_state.user.get('name', 'Kullanıcı')}")
    st.markdown("---")
    
    if st.button("🏠 Dashboard'a Dön"):
        st.switch_page("pages/dashboard.py")
    
    if st.button("➕ Yeni Lead Ekle"):
        st.switch_page("pages/new_lead.py")
    
    if st.button("🚪 Çıkış Yap"):
        st.session_state.token = None
        st.session_state.user = None
        st.switch_page("app.py")

# Ana içerik
st.markdown("<h1 style='text-align: center;'>Profil Düzenleme 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

# Kullanıcı bilgilerini al
try:
    user_response = requests.get(
        f"{API_URL}/users/me",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if user_response.status_code == 200:
        user = user_response.json()
        
        # Profil bilgileri
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Mevcut Bilgiler")
            st.write("**Ad:**", user.get('name', '-'))
            st.write("**E-posta:**", user.get('email', '-'))
            st.write("**Şirket:**", user.get('company', 'Belirtilmedi'))
            st.write("**Kayıt Tarihi:**", user.get('created_at', '-'))
        
        with col2:
            st.subheader("Bilgileri Güncelle")
            
            with st.form("update_profile_form"):
                new_name = st.text_input("Ad Soyad", value=user.get('name', ''))
                new_company = st.text_input("Şirket", value=user.get('company', ''))
                submit_button = st.form_submit_button("Güncelle", use_container_width=True)
            
            if submit_button:
                try:
                    with st.spinner("Güncelleniyor..."):
                        response = requests.put(
                            f"{API_URL}/users/me",
                            params={"name": new_name, "company": new_company},
                            headers={"Authorization": f"Bearer {st.session_state.token}"}
                        )
                    
                    if response.status_code == 200:
                        updated_user = response.json()
                        st.session_state.user = updated_user
                        st.success("✅ Profil başarıyla güncellendi!")
                        st.rerun()
                    else:
                        st.error("❌ Güncelleme hatası oluştu.")
                except Exception as e:
                    st.error(f"❌ Bağlantı hatası: {str(e)}")
        
        # Şifre değiştirme
        st.markdown("---")
        st.subheader("Şifre Değiştir")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Mevcut Şifre", type="password")
            new_password = st.text_input("Yeni Şifre", type="password")
            confirm_password = st.text_input("Yeni Şifre Tekrar", type="password")
            submit_button = st.form_submit_button("Şifreyi Değiştir", use_container_width=True)
        
        if submit_button:
            if not current_password or not new_password:
                st.warning("⚠️ Lütfen tüm alanları doldurun.")
            elif new_password != confirm_password:
                st.error("❌ Yeni şifreler eşleşmiyor.")
            elif len(new_password) < 6:
                st.error("❌ Şifre en az 6 karakter olmalı.")
            else:
                try:
                    # Önce mevcut şifreyi doğrula
                    login_response = requests.post(
                        f"{API_URL}/token",
                        data={"username": user['email'], "password": current_password}
                    )
                    
                    if login_response.status_code == 200:
                        # Şifre değiştir (password reset endpoint'ini kullan)
                        from auth import create_access_token
                        from datetime import timedelta
                        import jwt
                        import os
                        
                        reset_token = create_access_token(
                            data={"sub": user['email']},
                            expires_delta=timedelta(hours=1)
                        )
                        
                        reset_response = requests.post(
                            f"{API_URL}/password-reset/confirm",
                            params={"token": reset_token, "new_password": new_password}
                        )
                        
                        if reset_response.status_code == 200:
                            st.success("✅ Şifre başarıyla değiştirildi!")
                            st.info("Lütfen tekrar giriş yapın.")
                        else:
                            st.error("❌ Şifre değiştirme hatası.")
                    else:
                        st.error("❌ Mevcut şifre hatalı.")
                        
                except Exception as e:
                    st.error(f"❌ Hata: {str(e)}")
    else:
        st.error("Kullanıcı bilgisi alınamadı.")
        
except Exception as e:
    st.error(f"Bir hata oluştu: {str(e)}")
