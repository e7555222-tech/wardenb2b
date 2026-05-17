import streamlit as st
import requests
import re  # E-posta formatı kontrolü için ekledik (Regex)

# Sayfa Sekme Ayarları
st.set_page_config(page_title="Warden B2B Başvuru", page_icon="🏢")

st.title("Kurumsal Başvuru Ekranı 🔗")

# BURAYA KENDİ n8n CANLI (PRODUCTION) WEBHOOK LİNKİNİ YAPIŞTIR
WEBHOOK_URL = "https://emotpl.app.n8n.cloud/webhook/592b53b7-5a00-46ed-be21-c25b1b7b2d62"

# E-posta kontrolü için Regex (Düzenli İfade) kuralı: İçinde @ ve . olmak zorunda
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Form Alanı
with st.form("basvuru_formu"):
    name = st.text_input("Ad Soyad")
    email = st.text_input("E-posta Adresi")
    company_url = st.text_input("Şirket Web Sitesi (Örn: stripe.com)")
    
    # Bütçe girişini profesyonelleştirdiğimiz kısım
    budget = st.number_input("Planlanan Aylık Otomasyon Bütçesi (USD)", min_value=1000, value=15000, step=1000)
    
    submit_button = st.form_submit_button("Warden Analizini Başlat 🚀")

# Butona basıldığında çalışacak senaryo
if submit_button:
    # 1. KONTROL: Alanlar boş mu?
    if not name or not email or not company_url:
        st.warning("⚠️ Lütfen Warden analizine başlamadan önce tüm alanları eksiksiz doldurun.")
        
    # 2. KONTROL: E-posta formatı doğru mu? (örn: icinde @ ve . var mı?)
    elif not EMAIL_REGEX.match(email):
        st.error("❌ Lütfen geçerli bir e-posta adresi giriniz. (Örn: isim@sirket.com)")
        
    # Her şey tamamsa veriyi gönder
    else:
        payload = {
            "name": name,
            "email": email,
            "company_url": company_url,
            "budget": budget
        }
        
        try:
            with st.spinner("Warden verileri analiz ediyor..."):
                # Veriyi n8n'e postalıyoruz
                response = requests.post(WEBHOOK_URL, json=payload)
            
            # n8n'den "Aldım" (200) onayı gelirse:
            if response.status_code == 200:
                st.success("✅ Başvurunuz başarıyla sistemimize iletildi!")
                st.info("Warden yapay zeka analizini başlattı. Lütfen birkaç dakika içinde e-posta kutunuzu (ve spam klasörünü) kontrol edin.")
                st.balloons() # Şov kısmı
            else:
                st.error(f"Sistemsel bir hata oluştu. Hata Kodu: {response.status_code}")
                
        except Exception as e:
            st.error("Sunucuya bağlanılamadı. Lütfen bağlantınızı kontrol edin.")
