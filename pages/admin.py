import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Warden B2B - Admin", page_icon="🛡️", layout="wide")

API_URL = "http://localhost:8000"

# Login kontrolü
if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

# Admin kontrolü
try:
    user_response = requests.get(
        f"{API_URL}/users/me",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    if user_response.status_code == 200:
        user = user_response.json()
        st.session_state.user = user  # Session state'i güncelle
        if not user.get("is_admin", False):
            st.error("❌ Bu sayfaya erişim izniniz yok.")
            st.info(f"Admin durumu: {user.get('is_admin', False)}")
            st.switch_page("pages/dashboard.py")
except:
    st.error("❌ Kullanıcı bilgisi alınamadı.")
    st.switch_page("pages/dashboard.py")

# Sidebar
with st.sidebar:
    st.markdown(f"### 👑 Admin Panel")
    st.markdown(f"👋 {user.get('name', 'Admin')}")
    st.markdown("---")
    
    if st.button("🏠 Dashboard'a Dön"):
        st.switch_page("pages/dashboard.py")
    
    if st.button("🚪 Çıkış Yap"):
        st.session_state.token = None
        st.session_state.user = None
        st.switch_page("app.py")

# Ana içerik
st.markdown("<h1 style='text-align: center;'>Admin Paneli 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

# Tab seçimi
tab1, tab2 = st.tabs(["Kullanıcılar", "Lead'ler"])

# Kullanıcılar Tab
with tab1:
    st.subheader("Tüm Kullanıcılar")
    
    try:
        users_response = requests.get(
            f"{API_URL}/admin/users",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        
        if users_response.status_code == 200:
            users = users_response.json()
            
            if users:
                df = pd.DataFrame(users)
                display_columns = ['id', 'name', 'email', 'company', 'is_admin', 'created_at']
                df_display = df[display_columns]
                df_display.columns = ['ID', 'Ad', 'E-posta', 'Şirket', 'Admin', 'Kayıt Tarihi']
                df_display['Admin'] = df_display['Admin'].apply(lambda x: '✅' if x else '❌')
                
                st.dataframe(df_display, use_container_width=True, height=400)
                
                # Kullanıcı işlemleri
                st.markdown("---")
                st.subheader("Kullanıcı İşlemleri")
                
                selected_user = st.selectbox(
                    "İşlem yapılacak kullanıcı",
                    options=users,
                    format_func=lambda x: f"{x['name']} ({x['email']})"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if not selected_user['is_admin']:
                        if st.button("👑 Admin Yap", use_container_width=True):
                            try:
                                response = requests.put(
                                    f"{API_URL}/admin/users/{selected_user['id']}/make-admin",
                                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                                )
                                if response.status_code == 200:
                                    st.success("✅ Kullanıcı admin yapıldı!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Hata: {str(e)}")
                
                with col2:
                    if st.button("🗑️ Kullanıcıyı Sil", use_container_width=True):
                        try:
                            response = requests.delete(
                                f"{API_URL}/admin/users/{selected_user['id']}",
                                headers={"Authorization": f"Bearer {st.session_state.token}"}
                            )
                            if response.status_code == 200:
                                st.success("✅ Kullanıcı silindi!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Hata: {str(e)}")
            else:
                st.info("📋 Henüz kayıtlı kullanıcı yok.")
        else:
            st.error("Kullanıcılar yüklenemedi.")
            
    except Exception as e:
        st.error(f"Bir hata oluştu: {str(e)}")

# Lead'ler Tab
with tab2:
    st.subheader("Tüm Lead'ler")
    
    try:
        leads_response = requests.get(
            f"{API_URL}/admin/leads",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        
        if leads_response.status_code == 200:
            leads = leads_response.json()
            
            if leads:
                df = pd.DataFrame(leads)
                display_columns = ['id', 'name', 'email', 'company_url', 'budget', 'score', 'sentiment', 'created_at']
                df_display = df[display_columns]
                df_display.columns = ['ID', 'Ad', 'E-posta', 'Şirket', 'Bütçe', 'Skor', 'İlgi', 'Tarih']
                
                st.dataframe(df_display, use_container_width=True, height=400)
                
                # İstatistikler
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Toplam Lead", len(leads))
                with col2:
                    scored_leads = [l for l in leads if l['score'] is not None]
                    avg_score = sum(l['score'] for l in scored_leads) / len(scored_leads) if scored_leads else 0
                    st.metric("Ortalama Skor", f"{avg_score:.1f}")
                with col3:
                    high_leads = len([l for l in leads if l['score'] and l['score'] >= 80])
                    st.metric("Yüksek Nitelik", high_leads)
            else:
                st.info("📋 Henüz lead kaydı yok.")
        else:
            st.error("Lead'ler yüklenemedi.")
            
    except Exception as e:
        st.error(f"Bir hata oluştu: {str(e)}")
