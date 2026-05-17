import streamlit as st
import requests
import re

# Sayfa ayarları
st.set_page_config(page_title="Warden Automations", page_icon="🛡️", layout="centered")

# KENDİ n8n CANLI (PRODUCTION) WEBHOOK LİNKİNİ BURAYA YAPIŞTIR
WEBHOOK_URL = "https://emotpl.app.n8n.cloud/webhook/592b53b7-5a00-46ed-be21-c25b1b7b2d62"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Tasarımı toparlayan ana blok
with st.container():
    with st.form("basvuru_formu", clear_on_submit=False):
        # Marka İsmi ve Kalkan - Kurumsal Ağırlık Burada
        st.markdown("<h1 style='text-align: center;'>Warden Automations 🛡️</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #555;'>Kurumsal Başvuru ve Analiz Ekranı</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-style: italic;'> Müşteri Nitelendirme Sistemi</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        name = st.text_input("Ad Soyad")
        email = st.text_input("E-posta Adresi")
        company_url = st.text_input("Şirket Web Sitesi (Örn: stripe.com)")
        budget = st.number_input("Planlanan Aylık Otomasyon Bütçesi (USD)", min_value=1000, value=15000, step=1000)
        
        st.write("")
        submit_button = st.form_submit_button("Warden Analizini Başlat 🚀", use_container_width=True)

# Bildirimler
if submit_button:
    if not name or not email or not company_url:
        st.warning("⚠️ Lütfen analizden önce tüm alanları eksiksiz doldurun.")
    elif not EMAIL_REGEX.match(email):
        st.error("❌ Lütfen geçerli bir e-posta adresi giriniz.")
    else:
        payload = {"name": name, "email": email, "company_url": company_url, "budget": budget}
        try:
            with st.spinner("Warden analiz ediyor..."):
                response = requests.post(WEBHOOK_URL, json=payload)
            
            if response.status_code == 200:
                st.success("✅ Başvurunuz iletildi! Warden iş başında.")
                st.info("Analiz sonucu e-posta adresinize gönderilecektir.")
                st.balloons()
            else:
                st.error(f"Hata Kodu: {response.status_code}")
        except Exception as e:
            st.error("Bağlantı hatası oluştu.")
