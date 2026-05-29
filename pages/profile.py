import requests
import streamlit as st

from config import API_URL

st.set_page_config(page_title="Warden B2B - Profil", page_icon="🛡️", layout="centered")

if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

auth_headers = {"Authorization": f"Bearer {st.session_state.token}"}

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

st.markdown("<h1 style='text-align: center;'>Profil Düzenleme 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

try:
    user_response = requests.get(f"{API_URL}/users/me", headers=auth_headers, timeout=30)

    if user_response.status_code != 200:
        st.error("Kullanıcı bilgisi alınamadı.")
        st.stop()

    user = user_response.json()
    st.session_state.user = user

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Mevcut Bilgiler")
        st.write("**Ad:**", user.get("name", "-"))
        st.write("**E-posta:**", user.get("email", "-"))
        st.write("**Şirket:**", user.get("company") or "Belirtilmedi")
        if user.get("created_at"):
            st.write("**Kayıt Tarihi:**", user["created_at"])

    with col2:
        st.subheader("Bilgileri Güncelle")
        with st.form("update_profile_form"):
            new_name = st.text_input("Ad Soyad", value=user.get("name", ""))
            new_company = st.text_input("Şirket", value=user.get("company") or "")
            submit_profile = st.form_submit_button("Güncelle", use_container_width=True)

        if submit_profile:
            try:
                response = requests.put(
                    f"{API_URL}/users/me",
                    json={"name": new_name, "company": new_company},
                    headers=auth_headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    st.session_state.user = response.json()
                    st.success("✅ Profil güncellendi!")
                    st.rerun()
                else:
                    st.error("❌ Güncelleme hatası.")
            except requests.RequestException as exc:
                st.error(f"❌ Bağlantı hatası: {exc}")

    st.markdown("---")
    st.subheader("Şifre Değiştir")

    with st.form("change_password_form"):
        current_password = st.text_input("Mevcut Şifre", type="password")
        new_password = st.text_input("Yeni Şifre", type="password")
        confirm_password = st.text_input("Yeni Şifre Tekrar", type="password")
        submit_password = st.form_submit_button("Şifreyi Değiştir", use_container_width=True)

    if submit_password:
        if not current_password or not new_password:
            st.warning("⚠️ Lütfen tüm alanları doldurun.")
        elif new_password != confirm_password:
            st.error("❌ Yeni şifreler eşleşmiyor.")
        elif len(new_password) < 6:
            st.error("❌ Şifre en az 6 karakter olmalı.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/users/me/change-password",
                    json={
                        "current_password": current_password,
                        "new_password": new_password,
                    },
                    headers=auth_headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    st.success("✅ Şifre değiştirildi. Lütfen tekrar giriş yapın.")
                    st.session_state.token = None
                    st.session_state.user = None
                else:
                    detail = response.json().get("detail", "Şifre değiştirilemedi.")
                    st.error(f"❌ {detail}")
            except requests.RequestException as exc:
                st.error(f"❌ Bağlantı hatası: {exc}")

except requests.RequestException as exc:
    st.error(f"Bir hata oluştu: {exc}")
