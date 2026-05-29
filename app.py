import re

import requests
import streamlit as st

from config import API_URL

st.set_page_config(page_title="Warden B2B - Giriş", page_icon="🛡️", layout="centered")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None


def check_login():
    if st.session_state.token:
        st.switch_page("pages/dashboard.py")


check_login()

tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

with tab1:
    st.markdown("<h1 style='text-align: center;'>Warden B2B 🛡️</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #555;'>Giriş Yap</h3>", unsafe_allow_html=True)
    st.markdown("---")

    with st.form("login_form"):
        email = st.text_input("E-posta Adresi")
        password = st.text_input("Şifre", type="password")
        submit_button = st.form_submit_button("Giriş Yap", use_container_width=True)

    if submit_button:
        if not email or not password:
            st.warning("⚠️ Lütfen tüm alanları doldurun.")
        elif not EMAIL_REGEX.match(email):
            st.error("❌ Lütfen geçerli bir e-posta adresi giriniz.")
        else:
            try:
                with st.spinner("Giriş yapılıyor..."):
                    response = requests.post(
                        f"{API_URL}/token",
                        data={"username": email, "password": password},
                        timeout=30,
                    )

                if response.status_code == 200:
                    st.session_state.token = response.json()["access_token"]
                    user_response = requests.get(
                        f"{API_URL}/users/me",
                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                        timeout=30,
                    )
                    if user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                    st.success("✅ Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("❌ Hatalı e-posta veya şifre.")
            except requests.RequestException:
                st.error("❌ Bağlantı hatası. Backend'in çalıştığından emin olun.")

with tab2:
    st.markdown("<h1 style='text-align: center;'>Warden B2B 🛡️</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #555;'>Kayıt Ol</h3>", unsafe_allow_html=True)
    st.markdown("---")

    with st.form("register_form"):
        name = st.text_input("Ad Soyad")
        email = st.text_input("E-posta Adresi")
        company = st.text_input("Şirket (Opsiyonel)")
        password = st.text_input("Şifre", type="password")
        confirm_password = st.text_input("Şifre Tekrar", type="password")
        submit_button = st.form_submit_button("Kayıt Ol", use_container_width=True)

    if submit_button:
        if not name or not email or not password:
            st.warning("⚠️ Lütfen zorunlu alanları doldurun.")
        elif not EMAIL_REGEX.match(email):
            st.error("❌ Lütfen geçerli bir e-posta adresi giriniz.")
        elif password != confirm_password:
            st.error("❌ Şifreler eşleşmiyor.")
        elif len(password) < 6:
            st.error("❌ Şifre en az 6 karakter olmalı.")
        else:
            try:
                with st.spinner("Kayıt yapılıyor..."):
                    response = requests.post(
                        f"{API_URL}/register",
                        json={
                            "email": email,
                            "password": password,
                            "name": name,
                            "company": company or None,
                        },
                        timeout=30,
                    )

                if response.status_code == 200:
                    st.success("✅ Kayıt başarılı! Giriş yapabilirsiniz.")
                elif response.status_code == 400:
                    st.error("❌ Bu e-posta adresi zaten kayıtlı.")
                else:
                    st.error("❌ Kayıt hatası oluştu.")
            except requests.RequestException:
                st.error("❌ Bağlantı hatası. Backend'in çalıştığından emin olun.")
