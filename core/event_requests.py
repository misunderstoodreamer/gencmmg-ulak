"""Event request workflow: submission, decision and SLA tracking."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from streamlit.runtime.uploaded_file_manager import UploadedFile

from core import attachments, notifications, repository
from core.domain import (
    DATE_FORMAT,
    MIN_LEAD_DAYS,
    TIMESTAMP_FORMAT,
    ContactOutcome,
    RequestStatus,
)
from core.provinces import normalize_code

log = logging.getLogger(__name__)


@dataclass
class RequestDraft:
    province: str | None
    title: str
    event_date: date
    owner_name: str
    owner_title: str
    venue: str
    plan: str
    urgent: bool
    urgency_reason: str
    files: list[UploadedFile] = field(default_factory=list)
    no_attachment_reason: str = ""


class RequestAlreadyDecided(RuntimeError):
    pass


class RequestNotFound(RuntimeError):
    pass


def earliest_standard_date() -> date:
    return date.today() + timedelta(days=MIN_LEAD_DAYS)


def parse_timestamp(value: object) -> datetime | None:
    try:
        return datetime.strptime(str(value), TIMESTAMP_FORMAT)
    except ValueError:
        return None


def hours_waiting(row) -> float:
    submitted = parse_timestamp(row.get("talep_zamani", ""))
    if submitted is None:
        return 0.0
    return (datetime.now() - submitted).total_seconds() / 3600


def is_urgent(row) -> bool:
    return str(row.get("acil_mi", "")).strip().lower() in ("true", "1", "evet")


def submit_request(draft: RequestDraft, submitted_by: str) -> tuple[str, bool]:
    """Upload attachments and persist a new request. Returns (request_id, headquarters_notified).

    The request row is written only after every upload succeeds.
    """
    request_id = f"ETK-{uuid.uuid4().hex[:8].upper()}"
    uploaded = attachments.upload(request_id, draft.files) if draft.files else []
    record = {
        "etkinlik_id": request_id,
        "il_kodu": normalize_code(draft.province),
        "etkinlik_adi": draft.title.strip(),
        "etkinlik_tarihi": draft.event_date.strftime(DATE_FORMAT),
        "acil_mi": str(draft.urgent),
        "durum": RequestStatus.PENDING.value,
        "talep_zamani": datetime.now().strftime(TIMESTAMP_FORMAT),
        "acil_gerekce": draft.urgency_reason.strip() if draft.urgent else "",
        "temsilci_email": submitted_by.strip().lower(),
        "sorumlu_ad_soyad": draft.owner_name.strip(),
        "sorumlu_unvan": draft.owner_title.strip(),
        "etkinlik_yeri": draft.venue.strip(),
        "etkinlik_nasil": draft.plan.strip(),
        "ek_dosyalar": attachments.serialize(uploaded),
        "ek_dosya_yok_gerekce": "" if uploaded else draft.no_attachment_reason.strip(),
    }
    repository.append_request(record)

    try:
        notifications.send_new_request_notice(record)
        return record["etkinlik_id"], True
    except notifications.MailError:
        log.warning("New request notice failed for %s", record["etkinlik_id"])
        return record["etkinlik_id"], False


def decide_request(
    request_id: str,
    status: RequestStatus,
    contact: ContactOutcome,
    contacted_by: str,
    note: str,
    decided_by: str,
) -> tuple[dict, bool]:
    """Record an approval or rejection. Returns (updated_record, requester_notified)."""
    found = repository.get_request(request_id)
    if found is None:
        raise RequestNotFound(request_id)
    sheet_row, record = found
    if record.get("durum") != RequestStatus.PENDING:
        raise RequestAlreadyDecided(record.get("durum", ""))

    decided_at = datetime.now()
    submitted_at = parse_timestamp(record.get("talep_zamani")) or decided_at
    fields = {
        "durum": status.value,
        "merkez_aksiyon_zamani": decided_at.strftime(TIMESTAMP_FORMAT),
        "sla_farki_saat": str(round((decided_at - submitted_at).total_seconds() / 3600, 2)),
        "iletisim_yapildi": contact.value,
        "iletisim_yapan_kisi": contacted_by.strip() if contact != ContactOutcome.NONE else "",
        "onay_notu": note.strip(),
        "onaylayan_email": decided_by,
    }
    repository.update_request(sheet_row, fields)
    record.update(fields)

    try:
        notifications.send_decision_notice(record)
        return record, True
    except notifications.MailError:
        log.warning("Decision notice failed for %s", request_id)
        return record, False
