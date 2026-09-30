"""Reusable UI building blocks."""

from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from core import attachments, repository
from core.auth import SessionUser
from core.domain import (
    CONTACT_OUTCOME_LABELS,
    DATE_FORMAT,
    DISPLAY_DATE_FORMAT,
    DISPLAY_TIMESTAMP_FORMAT,
    SLA_HOURS,
    ContactOutcome,
    RequestStatus,
    role_label,
)
from core.event_requests import hours_waiting, is_urgent, parse_timestamp
from core.provinces import province_name

_STATUS_STYLE = {
    RequestStatus.PENDING: ("orange", ":material/schedule:"),
    RequestStatus.APPROVED: ("green", ":material/check_circle:"),
    RequestStatus.REJECTED: ("red", ":material/cancel:"),
}


def page_header(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    eyebrow_html = f'<p class="eyebrow">{escape(eyebrow)}</p>' if eyebrow else ""
    subtitle_html = f'<p class="subtitle">{escape(subtitle)}</p>' if subtitle else ""
    st.html(f'<div class="page-header">{eyebrow_html}<h1>{escape(title)}</h1>{subtitle_html}</div>')


def empty_state(title: str, text: str = "") -> None:
    with st.container(border=True, key="panel-empty"):
        st.html(f'<div class="empty-state"><strong>{escape(title)}</strong>{escape(text)}</div>')


def stat_row(stats: list[tuple[str, object]]) -> None:
    for column, (label, value) in zip(st.columns(len(stats)), stats):
        column.metric(label, value, border=True)


def format_date(value: object) -> str:
    try:
        return datetime.strptime(str(value), DATE_FORMAT).strftime(DISPLAY_DATE_FORMAT)
    except ValueError:
        return str(value or "-")


def format_timestamp(value: object) -> str:
    parsed = parse_timestamp(value)
    return parsed.strftime(DISPLAY_TIMESTAMP_FORMAT) if parsed else str(value or "-")


def load_requests(province: str | None = None) -> pd.DataFrame:
    """Fetch requests, surfacing backend failures instead of showing an empty list."""
    try:
        return repository.list_requests(province)
    except repository.RepositoryError as exc:
        st.error(f"Talepler yüklenemedi. {exc}", icon=":material/error:")
        return pd.DataFrame()


def status_counts(df: pd.DataFrame) -> dict[RequestStatus, int]:
    counts = df["durum"].value_counts() if not df.empty else {}
    return {status: int(counts.get(status.value, 0)) for status in RequestStatus}


def overdue_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    pending = df[df["durum"] == RequestStatus.PENDING]
    return sum(1 for _, row in pending.iterrows() if hours_waiting(row) >= SLA_HOURS)


def _field(label: str, value: object) -> str:
    text = str(value or "").strip()
    css = "field-value" if text else "field-value muted"
    return (
        f'<div><p class="field-label">{escape(label)}</p>'
        f'<p class="{css}">{escape(text or "Belirtilmedi")}</p></div>'
    )


def _attachments_field(row) -> str:
    files = attachments.parse(row.get("ek_dosyalar"))
    if files:
        links = "".join(
            f'<a class="attachment" href="{escape(f.url)}" target="_blank" rel="noopener noreferrer">{escape(f.name)}</a>'
            for f in files
        )
        return f'<div><p class="field-label">Ekler</p><div class="attachments">{links}</div></div>'
    reason = str(row.get("ek_dosya_yok_gerekce", "")).strip()
    return _field("Ekler", f"Dosya eklenmedi — {reason}" if reason else "")


def _badges(row, status: str) -> None:
    with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
        if is_urgent(row):
            st.badge("Acil", color="red", icon=":material/priority_high:")
        if status == RequestStatus.PENDING:
            waited = hours_waiting(row)
            if waited >= SLA_HOURS:
                st.badge(f"{int(waited)} saattir bekliyor", color="orange", icon=":material/timer:")
        color, icon = _STATUS_STYLE.get(status, ("gray", None))
        st.badge(status or "Bilinmiyor", color=color, icon=icon)


def _decision_summary(row) -> str:
    contact = str(row.get("iletisim_yapildi", "")).strip()
    try:
        contact = CONTACT_OUTCOME_LABELS[ContactOutcome(contact)]
    except ValueError:
        pass
    fields = [
        _field("Görüşme", contact),
        _field("Görüşen", row.get("iletisim_yapan_kisi")),
        _field("Karar veren", row.get("onaylayan_email")),
        _field("Karar zamanı", format_timestamp(row.get("merkez_aksiyon_zamani"))),
    ]
    note = _field("Karar notu", row.get("onay_notu"))
    return (
        f'<div class="decision-box"><div class="field-grid">{"".join(fields)}</div>'
        f'<div style="margin-top:.75rem">{note}</div></div>'
    )


def request_card(row, *, show_province: bool) -> DeltaGenerator:
    """Render a request summary. Returns the card container so callers can append actions."""
    request_id = str(row.get("etkinlik_id", ""))
    status = str(row.get("durum", ""))
    card = st.container(border=True, key=f"card-{request_id}")

    with card:
        head, badges = st.columns([3, 2], vertical_alignment="top")
        meta = [f"<code>{escape(request_id)}</code>"]
        if show_province:
            meta.append(escape(province_name(row.get("il_kodu", ""))))
        meta.append(f"Gönderildi {escape(format_timestamp(row.get('talep_zamani')))}")
        head.html(
            f'<p class="card-title">{escape(str(row.get("etkinlik_adi", "")))}</p>'
            f'<p class="card-meta">{" · ".join(meta)}</p>'
        )
        with badges:
            _badges(row, status)

        owner = " · ".join(
            v for v in (str(row.get("sorumlu_ad_soyad", "")).strip(), str(row.get("sorumlu_unvan", "")).strip()) if v
        )
        fields = [
            _field("Etkinlik tarihi", format_date(row.get("etkinlik_tarihi"))),
            _field("Yer", row.get("etkinlik_yeri")),
            _field("Referans sorumlu", owner),
            _field("Talebi açan", row.get("temsilci_email")),
        ]

        body = f'<div class="field-grid">{"".join(fields)}</div>'
        body += f'<div style="margin-top:.9rem">{_field("Etkinlik planı", row.get("etkinlik_nasil"))}</div>'
        if is_urgent(row):
            body += f'<div style="margin-top:.9rem">{_field("Acil gerekçesi", row.get("acil_gerekce"))}</div>'
        body += f'<div style="margin-top:.9rem">{_attachments_field(row)}</div>'
        if status and status != RequestStatus.PENDING:
            body += _decision_summary(row)
        st.html(body)

    return card


def sidebar_account(user: SessionUser, on_logout) -> None:
    with st.sidebar:
        st.html(
            f'<div class="account"><p class="account-email">{escape(user.email)}</p>'
            f'<p class="account-meta">{escape(role_label(user.role))} · '
            f"{escape(province_name(user.province))}</p></div>"
        )
        if st.button("Çıkış yap", icon=":material/logout:", width="stretch"):
            on_logout()
            st.rerun()
