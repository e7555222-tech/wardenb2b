import streamlit as st
import requests
import re

# Sayfa Sekme Ayarları (Genişliği sabitleyip şık durması için)
st.set_page_config(page_title="Warden B2B Başvuru", page_icon="🏢", layout="centered")

# BURAYA KENDİ n8n CANLI (PRODUCTION) WEBHOOK LİNKİNİ YAPIŞTIR
WEBHOOK_URL = "https://emotpl.app.n8n.cloud/webhook/592b53b7-5a00-46ed-be21-c25b1b7b2d62"

# E-posta kontrolü için Regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Tasarımı ortalamak ve ince uzun bir "kart" görünümü vermek için 3 kolon açıyoruz
# Sadece ortadaki (col2) kolonu kullanacağız.
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Formun içine başlığı alıyoruz ki o güzel çerçevenin içinde kalsın
    with st.form("basvuru_formu"):
        # st.title yerine daha zarif duran markdown başlık kullanıyoruz
        st.markdown("### Kurumsal Başvuru Ekranı 🔗") 
        st.markdown("---") # Araya ince bir ayıraç çizgisi
        
        name = st.text_input("Ad Soyad")
        email = st.text_input("E-posta Adresi")
        company_url = st.text_input("Şirket Web Sitesi (Örn: stripe.com)")
        budget = st.number_input("Planlanan Aylık Otomasyon Bütçesi (USD)", min_value=1000, value=15000, step=1000)
        
        # Form Butonu
        submit_button = st.form_submit_button("Warden Analizini Başlat 🚀")

# Butona basıldığında çalışacak uyarılar da formun altına (col2 içine) ortalanarak gelsin
if submit_button:
    with col2:
        if not name or not email or not company_url:
            st.warning("⚠️ Lütfen analizden önce tüm alanları eksiksiz doldurun.")
        elif not EMAIL_REGEX.match(email):
            st.error("❌ Lütfen geçerli bir e-posta adresi giriniz. (Örn: isim@sirket.com)")
        else:
            payload = {
                "name": name,
                "email": email,
                "company_url": company_url,
                "budget": budget
            }
            
            try:
                with st.spinner("Warden verileri analiz ediyor..."):
                    response = requests.post(WEBHOOK_URL, json=payload)
                
                if response.status_code == 200:
                    st.success("✅ Başvurunuz başarıyla sistemimize iletildi!")
                    st.info("Warden yapay zeka analizini başlattı. E-posta kutunuzu kontrol edin.")
                    st.balloons() 
                else:
                    st.error(f"Sistemsel bir hata oluştu. Hata Kodu: {response.status_code}")
                    
            except Exception as e:
                st.error("Sunucuya bağlanılamadı. Lütfen bağlantınızı kontrol edin.")
