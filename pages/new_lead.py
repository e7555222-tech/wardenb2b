import re

import requests
import streamlit as st

from config import API_URL, N8N_WEBHOOK_URL

st.set_page_config(page_title="Warden B2B - Yeni Lead", page_icon="🛡️", layout="centered")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

with st.sidebar:
    st.markdown(f"### 👋 {st.session_state.user.get('name', 'Kullanıcı')}")
    st.markdown("---")
    if st.button("🏠 Dashboard'a Dön"):
        st.switch_page("pages/dashboard.py")
    if st.button("🚪 Çıkış Yap"):
        st.session_state.token = None
        st.session_state.user = None
        st.switch_page("app.py")

st.markdown("<h1 style='text-align: center;'>Yeni Lead Ekle 🛡️</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Müşteri Nitelendirme Formu</h3>", unsafe_allow_html=True)
st.markdown("---")

if not N8N_WEBHOOK_URL:
    st.warning("N8N_WEBHOOK_URL tanımlı değil. Lead kaydedilir; otomatik analiz devre dışı.")

with st.form("new_lead_form", clear_on_submit=False):
    name = st.text_input("Ad Soyad")
    email = st.text_input("E-posta Adresi")
    company_name = st.text_input("Şirket Adı")
    has_website = st.radio("Müşterinin web sitesi var mı?", ["Evet", "Hayır"], horizontal=True)
    company_url = ""
    if has_website == "Evet":
        company_url = st.text_input("Şirket Web Sitesi (Örn: stripe.com)")
    budget = st.number_input(
        "Planlanan Aylık Otomasyon Bütçesi (USD)",
        min_value=1000,
        value=15000,
        step=1000,
    )
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button("💾 Kaydet ve Analiz Et", use_container_width=True)
    with col2:
        dashboard_button = st.form_submit_button("🏠 Dashboard'a Dön", use_container_width=True)

if dashboard_button:
    st.switch_page("pages/dashboard.py")

if submit_button:
    if not name or not email:
        st.warning("⚠️ Lütfen ad ve e-posta alanlarını doldurun.")
    elif has_website == "Evet" and not company_url:
        st.warning("⚠️ Web sitesi seçtiyseniz lütfen site adresini girin.")
    elif not EMAIL_REGEX.match(email):
        st.error("❌ Lütfen geçerli bir e-posta adresi giriniz.")
    else:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        resolved_url = company_url if has_website == "Evet" else None
        try:
            with st.spinner("Lead kaydediliyor..."):
                lead_response = requests.post(
                    f"{API_URL}/leads",
                    json={
                        "name": name,
                        "email": email,
                        "company_name": company_name or None,
                        "company_url": resolved_url,
                        "budget": budget,
                    },
                    headers=headers,
                    timeout=30,
                )

            if lead_response.status_code == 200:
                lead_data = lead_response.json()
                lead_id = lead_data["id"]

                if N8N_WEBHOOK_URL:
                    with st.spinner("Warden analiz ediyor..."):
                        webhook_payload = {
                            "name": name,
                            "email": email,
                            "company_name": company_name or None,
                            "company_url": resolved_url,
                            "budget": budget,
                            "lead_id": lead_id,
                            "user_id": st.session_state.user["id"],
                        }
                        webhook_response = requests.post(
                            N8N_WEBHOOK_URL, json=webhook_payload, timeout=60
                        )

                    if webhook_response.status_code == 200:
                        st.success("✅ Lead kaydedildi ve analiz için gönderildi!")
                        st.info("Analiz sonucu dashboard'da görüntülenecek.")
                        st.balloons()
                    else:
                        st.warning(
                            f"⚠️ Lead kaydedildi; webhook yanıtı: {webhook_response.status_code}"
                        )
                else:
                    st.success("✅ Lead kaydedildi.")

                if st.button("Dashboard'a Git"):
                    st.switch_page("pages/dashboard.py")
            elif lead_response.status_code == 403:
                st.error(f"❌ {lead_response.json().get('detail', 'Lead limitine ulaştınız.')}")
            else:
                st.error(f"❌ Kayıt hatası: {lead_response.status_code}")
        except requests.RequestException as exc:
            st.error(f"❌ Bağlantı hatası: {exc}")
