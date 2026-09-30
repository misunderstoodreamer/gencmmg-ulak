"""Submit a new event request."""

from datetime import date, timedelta

import streamlit as st

from core import attachments, repository, settings
from core.auth import require_role
from core.domain import (
    ATTACHMENT_MAX_FILES,
    ATTACHMENT_MAX_MB,
    ATTACHMENT_TYPES,
    DISPLAY_DATE_FORMAT,
    MIN_LEAD_DAYS,
    Role,
)
from core.event_requests import RequestDraft, earliest_standard_date, submit_request
from core.provinces import PROVINCES, province_label, province_names_summary
from core.validation import MIN_PLAN_LENGTH, validate_request
from ui.components import page_header

user = require_role(Role.BRANCH_PRESIDENT, Role.ADMIN)

_FORM_VERSION = "new_request_form_version"
_FLASH = "new_request_flash"
st.session_state.setdefault(_FORM_VERSION, 0)

page_header(
    "Yeni etkinlik talebi",
    subtitle="Talebiniz Genel Merkez onay havuzuna iletilir ve sonuç e-posta ile bildirilir.",
    eyebrow="Talepler",
)

if flash := st.session_state.pop(_FLASH, None):
    request_id, notified = flash
    st.success(f"Talebiniz alındı. Talep numarası: **{request_id}**", icon=":material/check_circle:")
    if not notified:
        st.warning("Genel Merkez'e bildirim e-postası gönderilemedi; talep yine de onay havuzunda.")

form_column, guide_column = st.columns([2.2, 1], gap="large")

with guide_column, st.container(border=True, key="panel-guide"):
    st.markdown("**Onay süreci**")
    st.markdown(
        f"""
1. Talebi eksiksiz doldurup gönderin.
2. Genel Merkez referans sorumluyla görüşür.
3. Karar ve not e-posta ile size iletilir.

**Tarih kuralı:** Standart etkinlikler en erken
**{earliest_standard_date().strftime(DISPLAY_DATE_FORMAT)}** tarihine planlanabilir
({MIN_LEAD_DAYS} gün). Daha yakın tarihler için talebi acil olarak işaretleyip gerekçe yazın.
"""
    )
    st.caption(f"Talep açılabilen iller: {province_names_summary()}.")

with form_column, st.container(border=True, key="panel-form"):
    with st.form(f"new_request_{st.session_state[_FORM_VERSION]}", border=False):
        st.markdown("##### Etkinlik")
        if user.is_admin:
            province = st.selectbox(
                "İl",
                options=list(PROVINCES),
                format_func=province_label,
                index=None,
                placeholder="İl seçin",
            )
        else:
            province = user.province
            st.text_input("İl", value=province_label(province), disabled=True)

        title = st.text_input("Etkinlik adı", max_chars=200, placeholder="Örn. Genç MMG Teknik Gezisi")
        date_column, venue_column = st.columns([1, 2])
        event_date = date_column.date_input(
            "Etkinlik tarihi",
            value=earliest_standard_date(),
            min_value=date.today() + timedelta(days=1),
            format="DD.MM.YYYY",
        )
        venue = venue_column.text_input(
            "Yer", max_chars=300, placeholder="Örn. Ankara Şubesi konferans salonu"
        )

        st.markdown("##### Referans sorumlu")
        st.caption("Onay sürecinde Genel Merkez'in görüşeceği, etkinliği temsil eden kişi.")
        name_column, title_column = st.columns(2)
        owner_name = name_column.text_input("Ad soyad", max_chars=120)
        owner_title = title_column.text_input("Unvan", max_chars=120, placeholder="Örn. Şube Başkanı")

        st.markdown("##### Etkinlik planı")
        plan = st.text_area(
            "Plan",
            label_visibility="collapsed",
            height=140,
            max_chars=1500,
            placeholder="Format, program akışı, beklenen katılımcı sayısı ve organizasyon şekli.",
            help=f"En az {MIN_PLAN_LENGTH} karakter.",
        )

        st.markdown("##### Öncelik")
        urgent = st.toggle("Acil talep", help=f"{MIN_LEAD_DAYS} günden yakın tarihli etkinlikler için gereklidir.")
        urgency_reason = st.text_area(
            "Acil gerekçesi",
            height=80,
            placeholder="Yalnızca acil talepler için doldurun.",
        )

        st.markdown("##### Ekler")
        uploads_enabled = settings.attachments_enabled()
        files = st.file_uploader(
            "Dosya ekle (isteğe bağlı)",
            type=ATTACHMENT_TYPES,
            accept_multiple_files=True,
            max_upload_size=ATTACHMENT_MAX_MB,
            disabled=not uploads_enabled,
            help=f"Program, afiş, bütçe vb. En fazla {ATTACHMENT_MAX_FILES} dosya, dosya başına {ATTACHMENT_MAX_MB} MB.",
        )
        if not uploads_enabled:
            st.caption("Dosya yükleme şu an kapalı; lütfen aşağıya nedenini kısaca yazın.")
        no_attachment_reason = st.text_input(
            "Dosya eklemiyorsanız nedeni",
            max_chars=300,
            placeholder="Örn. Program henüz kesinleşmedi",
        )

        submitted = st.form_submit_button("Onaya gönder", type="primary", icon=":material/send:")

    if submitted:
        draft = RequestDraft(
            province=province,
            title=title,
            event_date=event_date,
            owner_name=owner_name,
            owner_title=owner_title,
            venue=venue,
            plan=plan,
            urgent=urgent,
            urgency_reason=urgency_reason,
            files=files or [],
            no_attachment_reason=no_attachment_reason,
        )
        if errors := validate_request(draft):
            st.error("Lütfen aşağıdaki alanları düzeltin:\n\n" + "\n".join(f"- {e}" for e in errors))
        else:
            try:
                with st.spinner("Dosyalar yükleniyor ve talep kaydediliyor..." if draft.files else "Talep kaydediliyor..."):
                    result = submit_request(draft, submitted_by=user.email)
            except attachments.AttachmentError as exc:
                st.error(f"Dosyalar yüklenemedi, talep kaydedilmedi. {exc}")
            except repository.RepositoryError as exc:
                st.error(f"Talep kaydedilemedi. {exc}")
            else:
                st.session_state[_FLASH] = result
                st.session_state[_FORM_VERSION] += 1
                st.rerun()
