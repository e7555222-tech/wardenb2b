import streamlit as st
import requests
import re

st.set_page_config(page_title="Warden B2B - Yeni Lead", page_icon="🛡️", layout="centered")

API_URL = "http://localhost:8000"
WEBHOOK_URL = "https://emotpl.app.n8n.cloud/webhook/592b53b7-5a00-46ed-be21-c25b1b7b2d62"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Login kontrolü
if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

# Sidebar
with st.sidebar:
    st.markdown(f"### 👋 {st.session_state.user.get('name', 'Kullanıcı')}")
    st.markdown("---")
    
    if st.button("🏠 Dashboard'a Dön"):
        st.switch_page("pages/dashboard.py")
    
    if st.button("🚪 Çıkış Yap"):
        st.session_state.token = None
        st.session_state.user = None
        st.switch_page("app.py")

# Ana içerik
st.markdown("<h1 style='text-align: center;'>Yeni Lead Ekle 🛡️</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555;'>Müşteri Nitelendirme Formu</h3>", unsafe_allow_html=True)
st.markdown("---")

with st.form("new_lead_form", clear_on_submit=False):
    name = st.text_input("Ad Soyad")
    email = st.text_input("E-posta Adresi")
    company_name = st.text_input("Şirket Adı")
    
    has_website = st.radio("Müşterinin web sitesi var mı?", ["Evet", "Hayır"], horizontal=True)
    
    if has_website == "Evet":
        company_url = st.text_input("Şirket Web Sitesi (Örn: stripe.com)")
    else:
        company_url = "yok"
    
    budget = st.number_input("Planlanan Aylık Otomasyon Bütçesi (USD)", min_value=1000, value=15000, step=1000)
    
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
        # Önce backend'e kaydet
        try:
            with st.spinner("Lead kaydediliyor..."):
                lead_response = requests.post(
                    f"{API_URL}/leads",
                    json={
                        "name": name,
                        "email": email,
                        "company_name": company_name if company_name else None,
                        "company_url": company_url if has_website == "Evet" else None,
                        "budget": budget
                    },
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
            
            if lead_response.status_code == 200:
                lead_data = lead_response.json()
                lead_id = lead_data['id']
                
                # Sonra n8n webhook'a gönder
                with st.spinner("Warden analiz ediyor..."):
                    webhook_payload = {
                        "name": name,
                        "email": email,
                        "company_url": company_url,
                        "budget": budget,
                        "lead_id": lead_id,
                        "user_id": st.session_state.user['id']
                    }
                    webhook_response = requests.post(WEBHOOK_URL, json=webhook_payload)
                
                if webhook_response.status_code == 200:
                    st.success("✅ Lead kaydedildi ve analiz için gönderildi!")
                    st.info("Analiz sonucu dashboard'da görüntülenecek.")
                    st.balloons()
                    
                    if st.button("Dashboard'a Git"):
                        st.switch_page("pages/dashboard.py")
                else:
                    st.warning(f"⚠️ Lead kaydedildi ama webhook hatası: {webhook_response.status_code}")
                    st.info("Lead dashboard'da görüntülenebilir, manuel analiz gerekebilir.")
            elif lead_response.status_code == 403:
                st.error("❌ Lead limitine ulaştınız! Aboneliğinizi yükseltin.")
            else:
                st.error(f"❌ Kayıt hatası: {lead_response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Bağlantı hatası: {str(e)}")
