from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from config import API_URL

st.set_page_config(page_title="Warden B2B - Dashboard", page_icon="🛡️", layout="wide")

if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.switch_page("app.py")


auth_headers = {"Authorization": f"Bearer {st.session_state.token}"}

with st.sidebar:
    st.markdown(f"### 👋 {st.session_state.user.get('name', 'Kullanıcı')}")
    st.markdown(f"📧 {st.session_state.user.get('email', '')}")
    st.markdown(f"🏢 {st.session_state.user.get('company', 'Şirket belirtilmedi')}")
    st.markdown("---")

    try:
        sub_response = requests.get(f"{API_URL}/subscription", headers=auth_headers, timeout=30)
        if sub_response.status_code == 200:
            sub = sub_response.json()
            tier_icons = {"free": "🆓", "pro": "💎", "enterprise": "🏢"}
            limit = sub.get("lead_limit")
            limit_text = "Sınırsız" if limit is None else str(limit)
            st.markdown(
                f"### {tier_icons.get(sub['tier'], '📦')} {sub['tier'].upper()} Plan"
            )
            st.markdown(f"Durum: {sub['status']}")
            st.markdown(f"Lead limiti: {limit_text}")
    except requests.RequestException:
        st.warning("Abonelik bilgisi alınamadı")

    st.markdown("---")
    if st.button("👤 Profil"):
        st.switch_page("pages/profile.py")
    if st.button("➕ Yeni Lead"):
        st.switch_page("pages/new_lead.py")
    if st.session_state.user.get("is_admin"):
        if st.button("👑 Admin Panel"):
            st.switch_page("pages/admin.py")
    if st.button("Çıkış Yap"):
        logout()

st.markdown("<h1 style='text-align: center;'>Warden B2B Dashboard 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

try:
    leads_response = requests.get(f"{API_URL}/leads", headers=auth_headers, timeout=30)

    if leads_response.status_code == 200:
        leads = leads_response.json()

        if leads:
            df = pd.DataFrame(leads)
            for col in ("company_name", "company_url", "sentiment", "action", "score"):
                if col not in df.columns:
                    df[col] = None

            if "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

            def score_color(score):
                if score is None or pd.isna(score):
                    return "⚪"
                if score >= 80:
                    return "🟢"
                if score >= 50:
                    return "🟡"
                return "🔴"

            df["skor"] = df["score"].apply(score_color)

            display_columns = [
                "skor",
                "name",
                "email",
                "company_name",
                "company_url",
                "budget",
                "sentiment",
                "action",
            ]
            column_names = [
                "Skor",
                "Ad",
                "E-posta",
                "Şirket Adı",
                "Web Sitesi",
                "Bütçe (USD)",
                "İlgi",
                "Aksiyon",
            ]
            if "created_at" in df.columns:
                display_columns.append("created_at")
                column_names.append("Tarih")

            df_display = df[display_columns].copy()
            df_display.columns = column_names

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Toplam Lead", len(leads))
            with col2:
                scored = [l for l in leads if l.get("score") is not None]
                avg_score = sum(l["score"] for l in scored) / len(scored) if scored else 0
                st.metric("Ortalama Skor", f"{avg_score:.1f}")
            with col3:
                high = len([l for l in leads if l.get("score") and l["score"] >= 80])
                st.metric("Yüksek Nitelik", high)
            with col4:
                pending = len([l for l in leads if l.get("score") is None])
                st.metric("Bekleyen Analiz", pending)

            st.markdown("---")
            st.subheader("Lead Geçmişi")
            st.dataframe(df_display, use_container_width=True, height=400)

            st.download_button(
                label="📥 CSV Olarak İndir",
                data=df_display.to_csv(index=False).encode("utf-8"),
                file_name=f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.markdown("---")
            st.subheader("Lead Detayı")
            selected_lead = st.selectbox(
                "Detayını görüntüle",
                options=leads,
                format_func=lambda x: f"{x['name']} - {x.get('company_name') or 'Şirket yok'}",
            )

            if selected_lead:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Ad:**", selected_lead["name"])
                    st.write("**E-posta:**", selected_lead["email"])
                    st.write("**Şirket Adı:**", selected_lead.get("company_name") or "—")
                    st.write("**Web Sitesi:**", selected_lead.get("company_url") or "—")
                with c2:
                    st.write("**Bütçe:**", f"${selected_lead['budget']:,.0f}")
                    st.write("**Skor:**", selected_lead.get("score") or "Bekleniyor...")
                    st.write("**İlgi:**", selected_lead.get("sentiment") or "Bekleniyor...")
                    st.write("**Aksiyon:**", selected_lead.get("action") or "Bekleniyor...")
                    if selected_lead.get("created_at"):
                        st.write("**Kayıt Tarihi:**", selected_lead["created_at"])
        else:
            st.info("📋 Henüz lead yok. 'Yeni Lead' sayfasından ekleyebilirsiniz.")
    else:
        st.error("Lead'ler yüklenemedi.")

except requests.RequestException as exc:
    st.error(f"Bir hata oluştu: {exc}")
