from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

from config import API_URL, REQUEST_TIMEOUT

st.set_page_config(page_title="Warden B2B - Dashboard", page_icon="🛡️", layout="wide")

if "token" not in st.session_state or not st.session_state.token:
    st.switch_page("app.py")

auth_headers = {"Authorization": f"Bearer {st.session_state.token}"}


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.switch_page("app.py")


# ── Pre-fetch data ────────────────────────────────────────────────────────────
try:
    _leads_r = requests.get(f"{API_URL}/leads", headers=auth_headers, timeout=REQUEST_TIMEOUT)
    all_leads = _leads_r.json() if _leads_r.status_code == 200 else []
except requests.RequestException:
    all_leads = []

try:
    _sub_r = requests.get(f"{API_URL}/subscription", headers=auth_headers, timeout=REQUEST_TIMEOUT)
    sub = _sub_r.json() if _sub_r.status_code == 200 else None
except requests.RequestException:
    sub = None

scored_leads = [ld for ld in all_leads if ld.get("score") is not None]
pending_leads = [ld for ld in all_leads if ld.get("score") is None]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    user = st.session_state.user or {}
    st.markdown(f"### 👋 {user.get('name', 'Kullanıcı')}")
    st.markdown(f"📧 {user.get('email', '')}")
    if user.get("company"):
        st.markdown(f"🏢 {user['company']}")
    st.markdown("---")

    if sub:
        tier_icons = {"free": "🆓", "pro": "💎", "enterprise": "🏢"}
        tier = sub.get("tier", "free")
        limit = sub.get("lead_limit")
        st.markdown(f"**{tier_icons.get(tier, '📦')} {tier.upper()} Plan**")

        if limit is not None:
            used = len(all_leads)
            ratio = min(used / limit, 1.0)
            st.progress(ratio)
            color = "🔴" if ratio >= 0.9 else ("🟡" if ratio >= 0.7 else "🟢")
            st.caption(f"{color} {used}/{limit} lead kullanıldı")
        else:
            st.caption("♾️ Sınırsız lead")
    else:
        st.warning("Abonelik bilgisi alınamadı")

    st.markdown("---")
    if st.button("👤 Profil", use_container_width=True):
        st.switch_page("pages/profile.py")
    if st.button("➕ Yeni Lead", use_container_width=True):
        st.switch_page("pages/new_lead.py")
    if user.get("is_admin"):
        if st.button("👑 Admin Panel", use_container_width=True):
            st.switch_page("pages/admin.py")
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        logout()

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center;'>Warden B2B Dashboard 🛡️</h1>", unsafe_allow_html=True)
st.markdown("---")

# ── Metrics ───────────────────────────────────────────────────────────────────
avg_score = sum(ld["score"] for ld in scored_leads) / len(scored_leads) if scored_leads else 0
high_quality = len([ld for ld in scored_leads if ld["score"] >= 80])

c1, c2, c3, c4 = st.columns(4)
c1.metric("📋 Toplam Lead", len(all_leads))
c2.metric("📊 Ortalama Skor", f"{avg_score:.1f}")
c3.metric("🟢 Yüksek Nitelik", high_quality)
c4.metric("⏳ Bekleyen Analiz", len(pending_leads))

# ── AI Simülasyon ─────────────────────────────────────────────────────────────
if pending_leads:
    st.markdown("---")
    col_sim_l, col_sim_r = st.columns([3, 1])
    with col_sim_l:
        st.info(
            f"🤖 **{len(pending_leads)} lead** AI analizi bekliyor. "
            "n8n bağlantısı olmadan simüle edebilirsiniz."
        )
    with col_sim_r:
        if st.button(f"🤖 {len(pending_leads)} Analizi Simüle Et", use_container_width=True):
            progress_bar = st.progress(0)
            total_pending = len(pending_leads)
            for i, lead in enumerate(pending_leads):
                requests.post(
                    f"{API_URL}/leads/{lead['id']}/simulate-score",
                    headers=auth_headers,
                    timeout=REQUEST_TIMEOUT,
                )
                progress_bar.progress((i + 1) / total_pending)
            st.success("✅ Tüm analizler tamamlandı!")
            st.rerun()

# ── Charts ────────────────────────────────────────────────────────────────────
if scored_leads:
    st.markdown("---")
    st.subheader("📈 Analiz Grafikleri")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        score_df = (
            pd.DataFrame(scored_leads)[["name", "score"]]
            .sort_values("score", ascending=False)
            .head(10)
            .copy()
        )

        def _score_cat(s):
            return "Yüksek" if s >= 75 else ("Orta" if s >= 50 else "Düşük")

        score_df["nitelik"] = score_df["score"].apply(_score_cat)

        bar = (
            alt.Chart(score_df)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("score:Q", scale=alt.Scale(domain=[0, 100]), title="Skor"),
                y=alt.Y("name:N", sort="-x", title=""),
                color=alt.Color(
                    "nitelik:N",
                    scale=alt.Scale(
                        domain=["Yüksek", "Orta", "Düşük"],
                        range=["#00cc66", "#ffaa00", "#ff4444"],
                    ),
                    legend=alt.Legend(title="Nitelik"),
                ),
                tooltip=["name:N", "score:Q", "nitelik:N"],
            )
            .properties(title="En Yüksek Skorlu Leadler", height=max(len(score_df) * 38, 160))
        )
        st.altair_chart(bar, use_container_width=True)

    with chart_col2:
        sentiment_counts = (
            pd.DataFrame(scored_leads)["sentiment"]
            .value_counts()
            .reset_index()
        )
        sentiment_counts.columns = ["sentiment", "count"]

        donut = (
            alt.Chart(sentiment_counts)
            .mark_arc(innerRadius=55, outerRadius=100)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color(
                    "sentiment:N",
                    scale=alt.Scale(
                        domain=["Yüksek", "Orta", "Düşük"],
                        range=["#00cc66", "#ffaa00", "#ff4444"],
                    ),
                    legend=alt.Legend(title="İlgi Seviyesi"),
                ),
                tooltip=["sentiment:N", "count:Q"],
            )
            .properties(title="İlgi Seviyesi Dağılımı", height=260)
        )
        st.altair_chart(donut, use_container_width=True)

# ── Search & Filter ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Lead Geçmişi")

filter_col1, filter_col2 = st.columns([3, 1])
with filter_col1:
    search_term = st.text_input("🔍 Lead Ara", placeholder="İsim, şirket veya e-posta...")
with filter_col2:
    min_score_filter = st.slider("Min. Skor", 0, 100, 0)

if all_leads:
    df = pd.DataFrame(all_leads)
    for col in ("company_name", "company_url", "sentiment", "action", "score"):
        if col not in df.columns:
            df[col] = None

    # Client-side filtering
    mask = pd.Series([True] * len(df))
    if search_term:
        term = search_term.lower()
        mask &= (
            df["name"].str.lower().str.contains(term, na=False)
            | df.get("company_name", pd.Series([""] * len(df))).str.lower().str.contains(term, na=False)
            | df["email"].str.lower().str.contains(term, na=False)
        )
    if min_score_filter > 0:
        # Skoru olmayan (analiz bekleyen) lead'ler min-skor filtresine takılmaz —
        # backend davranışıyla tutarlı.
        mask &= df["score"].fillna(-1) >= min_score_filter

    filtered_df = df[mask].copy()

    if "created_at" in filtered_df.columns:
        filtered_df["created_at"] = pd.to_datetime(filtered_df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    def _score_icon(score):
        if score is None or pd.isna(score):
            return "⚪"
        if score >= 80:
            return "🟢"
        if score >= 50:
            return "🟡"
        return "🔴"

    filtered_df["skor"] = filtered_df["score"].apply(_score_icon)

    display_cols = ["skor", "name", "email", "company_name", "budget", "sentiment", "action"]
    col_names = ["Skor", "Ad", "E-posta", "Şirket", "Bütçe (USD)", "İlgi", "Aksiyon"]
    if "created_at" in filtered_df.columns:
        display_cols.append("created_at")
        col_names.append("Tarih")

    st.caption(f"{len(filtered_df)}/{len(all_leads)} lead gösteriliyor")
    st.dataframe(filtered_df[display_cols].rename(columns=dict(zip(display_cols, col_names))),
                 use_container_width=True, height=380)

    st.download_button(
        label="📥 CSV Olarak İndir",
        data=filtered_df[display_cols].rename(columns=dict(zip(display_cols, col_names))).to_csv(index=False).encode("utf-8"),
        file_name=f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ── Lead Detail ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔍 Lead Detayı")

    filtered_leads_list = filtered_df.to_dict("records") if not filtered_df.empty else []
    if filtered_leads_list:
        selected = st.selectbox(
            "Detayını görüntüle",
            options=all_leads,
            format_func=lambda x: f"{x['name']} — {x.get('company_name') or 'Şirket yok'}",
        )

        if selected:
            d1, d2 = st.columns(2)
            with d1:
                st.write("**Ad:**", selected["name"])
                st.write("**E-posta:**", selected["email"])
                st.write("**Şirket:**", selected.get("company_name") or "—")
                st.write("**Web Sitesi:**", selected.get("company_url") or "—")
                if selected.get("created_at"):
                    st.write("**Kayıt:**", selected["created_at"])
            with d2:
                st.write("**Bütçe:**", f"${selected['budget']:,.0f}")
                st.write("**Skor:**", selected.get("score") if selected.get("score") is not None else "Bekleniyor...")
                st.write("**İlgi:**", selected.get("sentiment") or "Bekleniyor...")
                st.write("**Aksiyon:**", selected.get("action") or "Bekleniyor...")

            if selected.get("score") is None:
                st.markdown("---")
                if st.button("🤖 Bu Lead'i AI ile Simüle Et", use_container_width=True):
                    with st.spinner("Warden analiz ediyor..."):
                        resp = requests.post(
                            f"{API_URL}/leads/{selected['id']}/simulate-score",
                            headers=auth_headers,
                            timeout=REQUEST_TIMEOUT,
                        )
                    if resp.status_code == 200:
                        st.success("✅ Analiz tamamlandı!")
                        st.rerun()
                    else:
                        st.error("❌ Simülasyon başarısız.")
    else:
        st.info("Filtreyle eşleşen lead bulunamadı.")
else:
    st.info("📋 Henüz lead yok. 'Yeni Lead' sayfasından ekleyebilirsiniz.")
