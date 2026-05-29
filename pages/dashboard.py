import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Warden B2B - Dashboard", page_icon="🛡️", layout="wide")

API_URL = "http://localhost:8000"

# Login kontrolü
if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

# Logout
def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.switch_page("app.py")

# Sidebar
with st.sidebar:
    st.markdown(f"### 👋 {st.session_state.user.get('name', 'Kullanıcı')}")
    st.markdown(f"📧 {st.session_state.user.get('email', '')}")
    st.markdown(f"🏢 {st.session_state.user.get('company', 'Şirket belirtilmedi')}")
    st.markdown("---")
    
    # Subscription bilgisi
    try:
        sub_response = requests.get(
            f"{API_URL}/subscription",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if sub_response.status_code == 200:
            sub = sub_response.json()
            tier_colors = {
                "free": "🆓",
                "pro": "💎",
                "enterprise": "🏢"
            }
            st.markdown(f"### {tier_colors.get(sub['tier'], '📦')} {sub['tier'].upper()} Plan")
            st.markdown(f"Durum: {sub['status']}")
    except:
        st.warning("Subscription bilgisi alınamadı")
    
    st.markdown("---")
    if st.button("Çıkış Yap"):
        logout()

# Ana içerik
st.markdown("<h1 style='text-align: center;'>Warden B2B Dashboard 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

# Lead'leri çek
try:
    leads_response = requests.get(
        f"{API_URL}/leads",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    
    if leads_response.status_code == 200:
        leads = leads_response.json()
        
        if leads:
            # DataFrame oluştur
            df = pd.DataFrame(leads)
            
            # Tarih formatla
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Skor renkleri
            def score_color(score):
                if score is None:
                    return "⚪"
                elif score >= 80:
                    return "🟢"
                elif score >= 50:
                    return "🟡"
                else:
                    return "🔴"
            
            df['skor'] = df['score'].apply(score_color)
            
            # Sütunları yeniden düzenle
            display_columns = ['skor', 'name', 'email', 'company_name', 'company_url', 'budget', 'sentiment', 'action']
            if 'created_at' in df.columns:
                display_columns.append('created_at')
            df_display = df[display_columns]
            df_display.columns = ['Skor', 'Ad', 'E-posta', 'Şirket Adı', 'Şirket', 'Bütçe (USD)', 'İlgi', 'Aksiyon']
            if 'created_at' in df.columns:
                df_display.columns = list(df_display.columns[:-1]) + ['Tarih']
            
            # İstatistikler
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Toplam Lead", len(leads))
            with col2:
                scored_leads = [l for l in leads if l['score'] is not None]
                avg_score = sum(l['score'] for l in scored_leads) / len(scored_leads) if scored_leads else 0
                st.metric("Ortalama Skor", f"{avg_score:.1f}")
            with col3:
                high_leads = len([l for l in leads if l['score'] and l['score'] >= 80])
                st.metric("Yüksek Nitelik", high_leads)
            with col4:
                pending_leads = len([l for l in leads if l['score'] is None])
                st.metric("Bekleyen Analiz", pending_leads)
            
            st.markdown("---")
            
            # Lead tablosu
            st.subheader("Lead Geçmişi")
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # CSV Export
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 CSV Olarak İndir",
                data=csv,
                file_name=f'leads_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                use_container_width=True
            )
            
            # Detay görünümü
            st.markdown("---")
            st.subheader("Lead Detayı")
            selected_lead = st.selectbox(
                "Detayını görüntüle",
                options=leads,
                format_func=lambda x: f"{x['name']} - {x.get('company_name', 'Şirket yok')}"
            )
            
            if selected_lead:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Ad:**", selected_lead['name'])
                    st.write("**E-posta:**", selected_lead['email'])
                    st.write("**Şirket Adı:**", selected_lead.get('company_name', 'Belirtilmedi'))
                    st.write("**Şirket Sitesi:**", selected_lead.get('company_url', 'Yok'))
                with col2:
                    st.write("**Bütçe:**", f"${selected_lead['budget']:,.0f}")
                    st.write("**Skor:**", selected_lead['score'] if selected_lead['score'] else "Bekleniyor...")
                    st.write("**İlgi:**", selected_lead['sentiment'] if selected_lead['sentiment'] else "Bekleniyor...")
                    st.write("**Aksiyon:**", selected_lead['action'] if selected_lead['action'] else "Bekleniyor...")
                if 'created_at' in selected_lead:
                    st.write("**Kayıt Tarihi:**", selected_lead['created_at'])
        else:
            st.info("📋 Henüz lead kaydınız yok. Yeni lead eklemek için 'Yeni Lead' sayfasına gidin.")
    else:
        st.error("Lead'ler yüklenemedi.")
        
except Exception as e:
    st.error(f"Bir hata oluştu: {str(e)}")

# Yeni lead butonu
st.markdown("---")
if st.button("➕ Yeni Lead Ekle", use_container_width=True):
    st.switch_page("pages/new_lead.py")
