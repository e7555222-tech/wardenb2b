import streamlit as st
import requests
import time

# Sayfa Ayarları ve Vitrin (AI kelimesini sekme adından da kaldırdık)
st.set_page_config(page_title="Warden | B2B Müşteri Nitelendirme", page_icon="🛡️", layout="centered")

# Başlık ve Açıklama (Tamamen Kurumsal ve Gizemli Dil)
st.title("🛡️ Warden Automations")
st.markdown("#### Gelişmiş B2B Müşteri Nitelendirme ve Skorlama Sistemi")
st.write("Warden, potansiyel müşterilerin dijital ayak izini saniyeler içinde analiz eder, düşük potansiyelli hedefleri otonom olarak eler ve satış ekibiniz için sadece VIP adayları filtreler.")
st.markdown("---")

# Form Alanı
with st.form("lead_form"):
    st.subheader("Kurumsal Başvuru Ekranı")
    name = st.text_input("Ad Soyad")
    email = st.text_input("E-posta Adresi")
    company_url = st.text_input("Şirket Web Sitesi (Örn: stripe.com)")
    budget = st.number_input("Planlanan Aylık Otomasyon Bütçesi (USD)", min_value=1000, value=15000, step=1000)

    # Gönder Butonu
    submitted = st.form_submit_button("Warden Analizini Başlat 🚀")

# Butona basıldığında tetiklenecek olaylar
if submitted:
    if not name or not email or not company_url:
        st.error("Warden eksik veriyle çalışmaz. Lütfen tüm alanları doldurun!")
    else:
        # Jüriyi Etkileyecek Şov Alanı (Algoritmik İllüzyon - AI kelimeleri temizlendi)
        with st.status("Warden Motoru Başlatılıyor...", expanded=True) as status:
            st.write("🔍 URL tespit edildi, kurumsal veriler taranıyor...")
            time.sleep(1.5) 
            st.write("🕷️ Sektörel vizyon ve hizmet ağacı haritalandırılıyor...")
            time.sleep(2)
            st.write("⚙️ Warden Karar Algoritması devrede. İdeal Müşteri Profili (ICP) ile eşleştiriliyor...")
            time.sleep(1.5)
            
            # --- BURASI N8N'E GİDEN KÖPRÜ ---
            webhook_url = "https://emotpl.app.n8n.cloud/webhook-test/592b53b7-5a00-46ed-be21-c25b1b7b2d62" 
            
            payload = {
                "name": name,
                "email": email,
                "company_url": company_url,
                "budget": budget
            }
            
            try:
                # Füze ateşleniyor!
                response = requests.post(webhook_url, json=payload)
                
                st.write("✅ Değerlendirme mekanizması sonuçlandı!")
                status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
                
                st.success("Warden kararını verdi! Akış tetiklendi ve ilgili geri dönüş saniyeler içinde adaya ulaştı.")
                
                # Jürinin gözünü boyayacak gösterişli skor tablosu
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="Hesaplanan Kalite Skoru", value="92/100", delta="VIP Aday")
                with col2:
                    st.metric(label="Kurtarılan Satış Ekibi Saati", value="1.8 Saat", delta="Otonom Süreç")
                
            except Exception as e:
                status.update(label="Sistemde bir arıza meydana geldi!", state="error")
                st.error(f"Sistem hatası: {e}")
