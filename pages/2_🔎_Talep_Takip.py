"""Talep Takip — İl Temsilcisi (kendi ili) & Admin (tümü)"""

import streamlit as st

from utils.auth import (
    ROLE_ADMIN,
    ROLE_IL_TEMSILCISI,
    can_view_all_requests,
    get_request_il_filter,
    init_session_state,
    is_admin,
    render_user_sidebar,
    require_role,
)
from utils.google_api import get_requests, hours_since_request, sheets_status_banner
from utils.iller import etiketten_kod, il_etiket, il_secenekleri
from utils.onay_kurallari import iletisim_ozet_markdown
from utils.talep_display import render_talep_karti
from utils.ui_styles import (
    apply_apple_style,
    glass_header,
    hide_sidebar_pages_for_role,
    set_sidebar_visible,
)

st.set_page_config(page_title="Talep Takip | Genç MMG", page_icon="🔎", layout="wide")

apply_apple_style()
init_session_state()
require_role([ROLE_IL_TEMSILCISI, ROLE_ADMIN])
set_sidebar_visible(True)
hide_sidebar_pages_for_role(st.session_state.rol)
render_user_sidebar()

sheets_status_banner()

if is_admin():
    glass_header("Talep Takip", "Admin modu — önemli illerin taleplerini görüntülüyorsunuz.")
    il_secim = st.selectbox("İl Filtresi", il_secenekleri(tumu=True))
    il_kodu = etiketten_kod(il_secim)
else:
    glass_header(
        "Talep Takip",
        f"{il_etiket(st.session_state.il_kodu)} kapsamındaki etkinlik talepleriniz.",
    )
    il_kodu = get_request_il_filter()

df = get_requests(il_kodu=il_kodu)

if df.empty:
    st.info("Henüz kayıtlı talep bulunmuyor.")
else:
    bekleyen = len(df[df["durum"] == "Bekliyor"])
    onayli = len(df[df["durum"] == "Onaylandı"])
    reddedilen = len(df[df["durum"] == "Reddedildi"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", len(df))
    c2.metric("Bekleyen", bekleyen)
    c3.metric("Onaylanan", onayli)
    c4.metric("Reddedilen", reddedilen)

    st.markdown("---")

    for _, row in df.sort_values("talep_zamani", ascending=False).iterrows():
        durum = str(row.get("durum", ""))
        hours = hours_since_request(str(row.get("talep_zamani", "")))
        onay_ozet = iletisim_ozet_markdown(row) if durum != "Bekliyor" else ""

        render_talep_karti(
            row,
            show_il=can_view_all_requests(),
            sla_hours=hours if durum == "Bekliyor" else None,
            durum=durum,
            onay_ozet_html=onay_ozet,
        )

    with st.expander("Ham veri tablosu"):
        st.dataframe(df, use_container_width=True, hide_index=True)
