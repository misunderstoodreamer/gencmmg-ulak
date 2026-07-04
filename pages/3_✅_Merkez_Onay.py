"""Merkez Onay Havuzu — Merkez Onaycı & Admin"""

import streamlit as st

from utils.auth import ROLE_ADMIN, ROLE_MERKEZ, init_session_state, render_user_sidebar, require_role
from utils.google_api import get_requests, hours_since_request, sheets_status_banner, update_request_status
from utils.iller import etiketten_kod, il_secenekleri
from utils.onay_kurallari import (
    ILETISIM_BEN,
    ILETISIM_SECENEKLERI,
    iletisim_ozet_markdown,
    validate_onay_form,
)
from utils.talep_display import render_talep_karti
from utils.ui_styles import (
    apply_apple_style,
    glass_header,
    hide_sidebar_pages_for_role,
    set_sidebar_visible,
)

st.set_page_config(page_title="Merkez Onay | Genç MMG", page_icon="✅", layout="wide")

apply_apple_style()
init_session_state()
require_role([ROLE_MERKEZ, ROLE_ADMIN])
set_sidebar_visible(True)
hide_sidebar_pages_for_role(st.session_state.rol)
render_user_sidebar()

sheets_status_banner()

glass_header(
    "Merkez Onay Havuzu",
    "Onaylamadan önce etkinlik sorumlusuyla iletişimi kaydedin.",
)

st.info(
    "**Onay kuralları:** Sorumluyu arayın → iletişimi kaydedin → en az 15 karakterlik not yazın → onaylayın."
)

df = get_requests()

if df.empty:
    st.warning("Henüz talep kaydı yok.")
    st.stop()

bekleyen_df = df[df["durum"] == "Bekliyor"]
sla_asan = sum(
    1 for _, r in bekleyen_df.iterrows()
    if hours_since_request(str(r.get("talep_zamani", ""))) >= 48
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam Talep", len(df))
c2.metric("Bekleyen", len(bekleyen_df))
c3.metric("SLA Aşan (48s+)", sla_asan)
c4.metric("Onaylanan", len(df[df["durum"] == "Onaylandı"]))

col_f1, col_f2 = st.columns(2)
with col_f1:
    filtre = st.selectbox("Durum Filtresi", ["Tümü", "Bekliyor", "Onaylandı", "Reddedildi"])
with col_f2:
    il_filtre = st.selectbox("İl Filtresi", il_secenekleri(tumu=True))

goster = df if filtre == "Tümü" else df[df["durum"] == filtre]
il_kod_filtre = etiketten_kod(il_filtre)
if il_kod_filtre:
    goster = goster[goster["il_kodu"].astype(str).str.zfill(2) == il_kod_filtre]
goster = goster.sort_values("talep_zamani", ascending=True)

st.markdown("---")

for _, row in goster.iterrows():
    etkinlik_id = str(row.get("etkinlik_id", ""))
    durum = str(row.get("durum", ""))
    hours = hours_since_request(str(row.get("talep_zamani", "")))
    onay_ozet = iletisim_ozet_markdown(row) if durum != "Bekliyor" else ""

    render_talep_karti(
        row,
        show_il=True,
        sla_hours=hours if durum == "Bekliyor" else None,
        durum=durum,
        onay_ozet_html=onay_ozet,
    )

    if durum == "Bekliyor":
        sorumlu_ref = f"{row.get('sorumlu_ad_soyad', '')} ({row.get('sorumlu_unvan', '')})"
        with st.expander(f"Onay / Red işlemi — {etkinlik_id}", expanded=True):
            with st.form(f"onay_form_{etkinlik_id}"):
                st.caption(f"Aranacak sorumlu: **{sorumlu_ref}**")

                iletisim_durumu = st.radio(
                    "Etkinlik sorumlusuyla iletişim",
                    ILETISIM_SECENEKLERI,
                    index=0,
                )

                iletisim_yapan = st.text_input(
                    "İletişime geçen kişi",
                    value=st.session_state.email,
                    placeholder="Ad soyad veya e-posta",
                )

                onay_notu = st.text_area(
                    "Onay / Red notu *",
                    placeholder=(
                        "Örn: 04.07.2026 14:30 — Çağatay Yağmur ile görüşüldü, "
                        "etkinlik teyit edildi, onaylandı."
                    ),
                    height=100,
                )

                col_onay, col_red = st.columns(2)
                onayla = col_onay.form_submit_button("✅ Onayla", use_container_width=True)
                reddet = col_red.form_submit_button("❌ Reddet", use_container_width=True)

                if onayla or reddet:
                    yapan = iletisim_yapan.strip()
                    if iletisim_durumu == ILETISIM_BEN:
                        yapan = yapan or st.session_state.email
                    yeni_durum = "Onaylandı" if onayla else "Reddedildi"

                    hatalar = validate_onay_form(iletisim_durumu, yapan, onay_notu, yeni_durum)
                    if hatalar:
                        for h in hatalar:
                            st.error(h)
                    else:
                        ok, msg = update_request_status(
                            etkinlik_id=etkinlik_id,
                            yeni_durum=yeni_durum,
                            temsilci_email=str(row.get("temsilci_email", "")),
                            etkinlik_adi=str(row.get("etkinlik_adi", "")),
                            iletisim_yapildi=iletisim_durumu,
                            iletisim_yapan_kisi=yapan,
                            onay_notu=onay_notu.strip(),
                            onaylayan_email=st.session_state.email,
                        )
                        if ok:
                            (st.success if onayla else st.warning)(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    st.markdown("")

with st.expander("Tüm veriler (tablo)"):
    st.dataframe(df, use_container_width=True, hide_index=True)
