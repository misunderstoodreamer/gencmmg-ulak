"""Yeni Etkinlik Talebi — İl Temsilcisi & Admin"""

from datetime import datetime, timedelta

import streamlit as st

from utils.auth import (
    ROLE_ADMIN,
    ROLE_IL_TEMSILCISI,
    init_session_state,
    is_admin,
    render_user_sidebar,
    require_role,
)
from utils.google_api import create_request, sheets_status_banner, validate_14_day_rule
from utils.iller import etiketten_kod, il_etiket, il_secenekleri
from utils.talep_display import validate_talep_detaylari
from utils.ui_styles import apply_apple_style, glass_header, hide_sidebar_pages_for_role, set_sidebar_visible

st.set_page_config(
    page_title="Yeni Talep | Genç MMG",
    page_icon="📝",
    layout="wide",
)

apply_apple_style()
init_session_state()
require_role([ROLE_IL_TEMSILCISI, ROLE_ADMIN])
set_sidebar_visible(True)
hide_sidebar_pages_for_role(st.session_state.rol)
render_user_sidebar()

sheets_status_banner()

subtitle = il_etiket(st.session_state.il_kodu)
if is_admin():
    subtitle = "Admin modu — önemli illerden biri için talep oluşturabilirsiniz."

glass_header("Yeni Etkinlik Talebi", subtitle)

min_tarih = datetime.now().date() + timedelta(days=1)
onerilen_min = datetime.now().date() + timedelta(days=14)

st.info(
    f"Standart etkinlikler için en erken tarih: **{onerilen_min.strftime('%d.%m.%Y')}** "
    "(14 gün kuralı). Onaya göndermeden önce referans sorumlu ve etkinlik detaylarını eksiksiz doldurun."
)

st.caption("Geçerli iller: Ankara, İzmir, Yalova, Kayseri, Sakarya, Gaziantep, Elazığ, Ağrı.")

with st.form("yeni_talep_form", clear_on_submit=True):
    st.markdown("#### 1. Etkinlik Bilgileri")

    if is_admin():
        il_secim = st.selectbox("İl *", il_secenekleri())
        il_kodu = etiketten_kod(il_secim)
    else:
        il_kodu = st.session_state.il_kodu
        st.text_input("İl", value=il_etiket(il_kodu), disabled=True)

    etkinlik_adi = st.text_input(
        "Etkinlik Adı *",
        placeholder="Örn: Genç MMG Teknik Gezi",
        max_chars=200,
    )

    etkinlik_tarihi = st.date_input(
        "Etkinlik Tarihi *",
        min_value=min_tarih,
        value=onerilen_min,
    )

    st.markdown("#### 2. Referans Sorumlu")
    st.caption("Onay sürecinde iletişim kurulacak, projeyi temsil eden kişi.")

    col_ad, col_unvan = st.columns(2)
    with col_ad:
        sorumlu_ad_soyad = st.text_input(
            "Sorumlu Ad Soyad *",
            placeholder="Örn: Ayşe Yılmaz",
            max_chars=120,
        )
    with col_unvan:
        sorumlu_unvan = st.text_input(
            "Unvan *",
            placeholder="Örn: İl Temsilcisi / Mimar",
            max_chars=120,
        )

    st.markdown("#### 3. Etkinlik Detayları")

    etkinlik_yeri = st.text_input(
        "Nerede Yapılacak? *",
        placeholder="Örn: Ankara MMG Şubesi konferans salonu / İzmir fuar alanı",
        max_chars=300,
    )

    etkinlik_nasil = st.text_area(
        "Nasıl Yapılacak? *",
        placeholder=(
            "Etkinliğin formatını, program akışını, katılımcı sayısını ve "
            "organizasyon şeklini kısaca açıklayın."
        ),
        height=120,
        max_chars=1500,
    )

    st.markdown("#### 4. Öncelik")
    acil_mi = st.checkbox("Acil Etkinlik")
    acil_gerekce = st.text_area(
        "Acil Etkinlik Gerekçesi (acil işaretliyse zorunlu)",
        placeholder="14 günden yakın tarihli etkinlikler için zorunludur.",
        height=80,
    )

    submitted = st.form_submit_button("Onaya Gönder", use_container_width=True)

    if submitted:
        hatalar = []

        if not etkinlik_adi.strip():
            hatalar.append("Etkinlik adı zorunludur.")

        if is_admin() and not il_kodu:
            hatalar.append("İl seçimi zorunludur.")

        hatalar.extend(
            validate_talep_detaylari(
                sorumlu_ad_soyad, sorumlu_unvan, etkinlik_yeri, etkinlik_nasil
            )
        )

        event_dt = datetime.combine(etkinlik_tarihi, datetime.min.time())
        valid, msg = validate_14_day_rule(event_dt, acil_mi)
        if not valid:
            hatalar.append(msg)

        if acil_mi and not acil_gerekce.strip():
            hatalar.append("Acil etkinlikler için gerekçe alanı zorunludur.")

        if hatalar:
            for h in hatalar:
                st.error(h)
        else:
            ok, result_msg = create_request(
                il_kodu=str(il_kodu).zfill(2),
                etkinlik_adi=etkinlik_adi,
                etkinlik_tarihi=event_dt,
                acil_mi=acil_mi,
                acil_gerekce=acil_gerekce if acil_mi else "",
                temsilci_email=st.session_state.email,
                sorumlu_ad_soyad=sorumlu_ad_soyad,
                sorumlu_unvan=sorumlu_unvan,
                etkinlik_yeri=etkinlik_yeri,
                etkinlik_nasil=etkinlik_nasil,
            )
            if ok:
                st.success(result_msg)
                st.balloons()
            else:
                st.error(result_msg)
