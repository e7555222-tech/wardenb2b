# 🧠 Müşterim AI | Otonom Lead Nitelendirme Paneli

> **Warden Automations - AI Engine**

Müşterim AI, B2B işletmelerine gelen potansiyel müşteri (lead) verilerini saniyeler içinde analiz eden, bütçe/zaman çizelgelerine göre skorlayan ve satış ekibine aksiyon öneren otonom bir analiz panelidir.

## 📸 Demo
![Müşterim AI Dashboard](screenshot.png)

## ⚡ Özellikler (Features)
* **Gerçek Zamanlı Analiz (Real-time Scoring):** Gelen veriyi anında işler ve 0-100 arası bir nitelik skoru atar.
* **İlgi Seviyesi (Sentiment Analysis):** Müşterinin potansiyelini Yüksek/Orta/Düşük olarak kategorize eder.
* **Aksiyon Motoru:** Satış ekibine "Hemen Aranmalı" veya "E-posta ile Beslenmeli (Nurture)" gibi net direktifler verir.
* **Karanlık Tema (Dark Mode UI):** Warden Automations kurumsal kimliğine tam uyumlu, enterprise seviyesi dashboard.

## 🔄 Nasıl Çalışır? (The Pipeline)
Sistem sadece bir arayüzden ibaret değildir, arkada **n8n** destekli otonom bir akış (workflow) çalışır:
1. **Veri Yakalama:** Sisteme yeni bir lead düştüğünde (veya Data Hunter veri çektiğinde) n8n Webhook'u tetiklenir.
2. **Yapay Zeka Analizi:** Veriler otonom olarak OpenAI API'sine gönderilir; NLP (Doğal Dil İşleme) ile niyet ve bütçe analizi yapılır.
3. **Karar Mekanizması:** Çıkan skor Streamlit paneline yansıtılır.
4. **Otonom Aksiyon:** Nitelik skoru yüksek (Örn: 80+) olan lead'ler için Gmail entegrasyonu üzerinden satış ekibine anında alarm e-postası gönderilir.

## 🛠️ Tech Stack
* **Language:** Python 3.x
* **Frontend/UI:** Streamlit
* **Workflow Automation:** n8n
* **AI Engine:** OpenAI GPT-4
* **Data Handling:** Pandas

## ⚙️ Kurulum (Local Setup)

1. Repoyu klonlayın ve klasöre girin:
```bash
git clone [https://github.com/USERNAME/warden-streamlit.git](https://github.com/USERNAME/warden-streamlit.git)
cd warden-streamlit
pip install -r requirements.txt
streamlit run app.py
```

## 🔑 Environment Variables
`.env` dosyası oluşturun:
OPENAI_API_KEY=your_key_here

> ⚠️ `.env` dosyanızı `.gitignore`'a eklemeyi unutmayın.
