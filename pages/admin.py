import pandas as pd
import requests
import streamlit as st

from config import API_URL

st.set_page_config(page_title="Warden B2B - Admin", page_icon="🛡️", layout="wide")

if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

auth_headers = {"Authorization": f"Bearer {st.session_state.token}"}

try:
    user_response = requests.get(f"{API_URL}/users/me", headers=auth_headers, timeout=30)
    if user_response.status_code != 200:
        st.error("Kullanıcı bilgisi alınamadı.")
        st.switch_page("pages/dashboard.py")
    user = user_response.json()
    st.session_state.user = user
    if not user.get("is_admin", False):
        st.error("❌ Bu sayfaya erişim izniniz yok.")
        st.switch_page("pages/dashboard.py")
except requests.RequestException:
    st.error("❌ Backend'e ulaşılamadı.")
    st.switch_page("pages/dashboard.py")

with st.sidebar:
    st.markdown("### 👑 Admin Panel")
    st.markdown(f"👋 {user.get('name', 'Admin')}")
    st.markdown("---")
    if st.button("🏠 Dashboard'a Dön"):
        st.switch_page("pages/dashboard.py")
    if st.button("🚪 Çıkış Yap"):
        st.session_state.token = None
        st.session_state.user = None
        st.switch_page("app.py")

st.markdown("<h1 style='text-align: center;'>Admin Paneli 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

tab1, tab2 = st.tabs(["Kullanıcılar", "Lead'ler"])

with tab1:
    st.subheader("Tüm Kullanıcılar")
    try:
        users_response = requests.get(
            f"{API_URL}/admin/users", headers=auth_headers, timeout=30
        )
        if users_response.status_code == 200:
            users = users_response.json()
            if users:
                df = pd.DataFrame(users)
                df_display = df[["id", "name", "email", "company", "is_admin", "created_at"]]
                df_display.columns = ["ID", "Ad", "E-posta", "Şirket", "Admin", "Kayıt Tarihi"]
                df_display["Admin"] = df_display["Admin"].apply(lambda x: "✅" if x else "❌")
                st.dataframe(df_display, use_container_width=True, height=400)

                st.markdown("---")
                selected_user = st.selectbox(
                    "İşlem yapılacak kullanıcı",
                    options=users,
                    format_func=lambda x: f"{x['name']} ({x['email']})",
                )
                col1, col2 = st.columns(2)
                with col1:
                    if not selected_user["is_admin"]:
                        if st.button("👑 Admin Yap", use_container_width=True):
                            resp = requests.put(
                                f"{API_URL}/admin/users/{selected_user['id']}/make-admin",
                                headers=auth_headers,
                                timeout=30,
                            )
                            if resp.status_code == 200:
                                st.success("✅ Kullanıcı admin yapıldı!")
                                st.rerun()
                with col2:
                    if st.button("🗑️ Kullanıcıyı Sil", use_container_width=True):
                        resp = requests.delete(
                            f"{API_URL}/admin/users/{selected_user['id']}",
                            headers=auth_headers,
                            timeout=30,
                        )
                        if resp.status_code == 200:
                            st.success("✅ Kullanıcı silindi!")
                            st.rerun()
            else:
                st.info("📋 Henüz kayıtlı kullanıcı yok.")
        else:
            st.error("Kullanıcılar yüklenemedi.")
    except requests.RequestException as exc:
        st.error(f"Bir hata oluştu: {exc}")

with tab2:
    st.subheader("Tüm Lead'ler")
    try:
        leads_response = requests.get(
            f"{API_URL}/admin/leads", headers=auth_headers, timeout=30
        )
        if leads_response.status_code == 200:
            leads = leads_response.json()
            if leads:
                df = pd.DataFrame(leads)
                for col in ("company_name", "company_url", "score", "sentiment"):
                    if col not in df.columns:
                        df[col] = None
                df_display = df[
                    [
                        "id",
                        "name",
                        "email",
                        "company_name",
                        "company_url",
                        "budget",
                        "score",
                        "sentiment",
                        "created_at",
                    ]
                ]
                df_display.columns = [
                    "ID",
                    "Ad",
                    "E-posta",
                    "Şirket",
                    "Site",
                    "Bütçe",
                    "Skor",
                    "İlgi",
                    "Tarih",
                ]
                st.dataframe(df_display, use_container_width=True, height=400)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Toplam Lead", len(leads))
                with col2:
                    scored = [l for l in leads if l.get("score") is not None]
                    avg = sum(l["score"] for l in scored) / len(scored) if scored else 0
                    st.metric("Ortalama Skor", f"{avg:.1f}")
                with col3:
                    high = len([l for l in leads if l.get("score") and l["score"] >= 80])
                    st.metric("Yüksek Nitelik", high)
            else:
                st.info("📋 Henüz lead kaydı yok.")
        else:
            st.error("Lead'ler yüklenemedi.")
    except requests.RequestException as exc:
        st.error(f"Bir hata oluştu: {exc}")
