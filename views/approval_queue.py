"""Headquarters approval queue."""

import streamlit as st

from core import repository
from core.auth import require_role
from core.domain import CONTACT_OUTCOME_LABELS, SLA_HOURS, ContactOutcome, RequestStatus, Role
from core.event_requests import RequestAlreadyDecided, RequestNotFound, decide_request
from core.provinces import PROVINCES, province_label
from core.validation import MIN_DECISION_NOTE_LENGTH, validate_decision
from ui.components import (
    empty_state,
    load_requests,
    overdue_count,
    page_header,
    request_card,
    stat_row,
    status_counts,
)

ALL = "all"
_FLASH = "approval_flash"

user = require_role(Role.APPROVER, Role.ADMIN)


@st.dialog("Talebi değerlendir", width="large")
def review_dialog(row) -> None:
    request_id = str(row["etkinlik_id"])
    st.markdown(f"**{row['etkinlik_adi']}**  \n`{request_id}` · {province_label(row['il_kodu'])}")
    st.info(
        f"Aranacak sorumlu: **{row.get('sorumlu_ad_soyad', '')}** ({row.get('sorumlu_unvan', '')})",
        icon=":material/call:",
    )

    with st.form(f"review_{request_id}", border=False):
        contact = st.radio(
            "Etkinlik sorumlusuyla görüşme",
            options=list(ContactOutcome),
            format_func=CONTACT_OUTCOME_LABELS.get,
        )
        contacted_by = st.text_input(
            "Görüşmeyi yapan",
            value=user.email,
            help="Başka biri görüştüyse adını ve soyadını yazın.",
        )
        note = st.text_area(
            "Karar notu",
            height=120,
            placeholder="Örn. 04.07.2026 14:30 — sorumlu ile görüşüldü, program ve mekân teyit edildi.",
            help=f"En az {MIN_DECISION_NOTE_LENGTH} karakter; görüşme özeti ve karar gerekçesi.",
        )
        approve_column, reject_column = st.columns(2)
        approve = approve_column.form_submit_button(
            "Onayla", type="primary", icon=":material/check:", width="stretch"
        )
        reject = reject_column.form_submit_button("Reddet", icon=":material/close:", width="stretch")

    if not (approve or reject):
        return

    status = RequestStatus.APPROVED if approve else RequestStatus.REJECTED
    if errors := validate_decision(status, contact, contacted_by, note):
        st.error("\n".join(f"- {e}" for e in errors))
        return

    try:
        with st.spinner("Karar kaydediliyor..."):
            _, notified = decide_request(
                request_id,
                status=status,
                contact=contact,
                contacted_by=contacted_by,
                note=note,
                decided_by=user.email,
            )
    except RequestAlreadyDecided as exc:
        st.warning(f"Bu talep başka bir kullanıcı tarafından zaten sonuçlandırılmış ({exc}).")
        return
    except RequestNotFound:
        st.error("Talep bulunamadı; silinmiş olabilir.")
        return
    except repository.RepositoryError as exc:
        st.error(f"Karar kaydedilemedi. {exc}")
        return

    st.session_state[_FLASH] = (request_id, status, notified)
    st.rerun()


page_header(
    "Onay havuzu",
    subtitle="Onay vermeden önce etkinlik sorumlusuyla görüşüp görüşme özetini kaydedin.",
    eyebrow="Genel Merkez",
)

if flash := st.session_state.pop(_FLASH, None):
    request_id, status, notified = flash
    st.toast(f"{request_id} {status.lower()}.", icon=":material/check_circle:")
    if not notified:
        st.warning(f"{request_id} için temsilciye bildirim e-postası gönderilemedi.")

df = load_requests()
if df.empty:
    empty_state("Henüz talep yok", "İllerden gelen talepler burada listelenir.")
    st.stop()

counts = status_counts(df)
stat_row(
    [
        ("Bekleyen", counts[RequestStatus.PENDING]),
        (f"{SLA_HOURS} saati aşan", overdue_count(df)),
        ("Onaylanan", counts[RequestStatus.APPROVED]),
        ("Reddedilen", counts[RequestStatus.REJECTED]),
    ]
)
st.space("small")

with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
    status = st.segmented_control(
        "Durum",
        options=[ALL, *RequestStatus],
        format_func=lambda s: "Tümü" if s == ALL else str(s),
        default=RequestStatus.PENDING,
        required=True,
        label_visibility="collapsed",
    )
    province = st.selectbox(
        "İl",
        options=[ALL, *PROVINCES],
        format_func=lambda code: "Tüm iller" if code == ALL else province_label(code),
        width=240,
        label_visibility="collapsed",
    )

visible = df if status == ALL else df[df["durum"] == status]
if province != ALL:
    visible = visible[visible["il_kodu"] == province]
# Oldest first so the longest-waiting requests are handled first.
visible = visible.sort_values("talep_zamani", ascending=True)

if visible.empty:
    empty_state("Filtreye uyan talep yok")

for _, row in visible.iterrows():
    card = request_card(row, show_province=True)
    if row["durum"] == RequestStatus.PENDING:
        with card:
            if st.button("Değerlendir", key=f"review-{row['etkinlik_id']}", icon=":material/rate_review:"):
                review_dialog(row)
