"""Form validation rules."""

from __future__ import annotations

from core.domain import ATTACHMENT_MAX_FILES, ATTACHMENT_MAX_MB, ContactOutcome, RequestStatus
from core.event_requests import RequestDraft, earliest_standard_date
from core.provinces import is_valid_province

MIN_PLAN_LENGTH = 20
MIN_DECISION_NOTE_LENGTH = 15


def validate_request(draft: RequestDraft) -> list[str]:
    errors = []
    if not draft.province or not is_valid_province(draft.province):
        errors.append("Geçerli bir il seçin.")
    if not draft.title.strip():
        errors.append("Etkinlik adı zorunludur.")
    if not draft.owner_name.strip():
        errors.append("Sorumlu kişinin adı soyadı zorunludur.")
    if not draft.owner_title.strip():
        errors.append("Sorumlu kişinin unvanı zorunludur.")
    if not draft.venue.strip():
        errors.append("Etkinlik yeri zorunludur.")
    if len(draft.plan.strip()) < MIN_PLAN_LENGTH:
        errors.append(f"Etkinlik planı en az {MIN_PLAN_LENGTH} karakter olmalıdır.")
    if draft.event_date < earliest_standard_date() and not draft.urgent:
        errors.append(
            "Etkinlik tarihi en az 14 gün sonrası olmalıdır. "
            "Daha yakın tarihli etkinlikler için talebi acil olarak işaretleyin."
        )
    if draft.urgent and not draft.urgency_reason.strip():
        errors.append("Acil talepler için gerekçe zorunludur.")
    if len(draft.files) > ATTACHMENT_MAX_FILES:
        errors.append(f"En fazla {ATTACHMENT_MAX_FILES} dosya eklenebilir.")
    if oversized := [f.name for f in draft.files if f.size > ATTACHMENT_MAX_MB * 1024 * 1024]:
        errors.append(f"{ATTACHMENT_MAX_MB} MB sınırını aşan dosyalar: {', '.join(oversized)}.")
    if not draft.files and not draft.no_attachment_reason.strip():
        errors.append("Dosya eklemiyorsanız nedenini belirtin.")
    return errors


def validate_decision(
    status: RequestStatus,
    contact: ContactOutcome,
    contacted_by: str,
    note: str,
) -> list[str]:
    errors = []
    if status == RequestStatus.APPROVED and contact == ContactOutcome.NONE:
        errors.append("Onay vermeden önce etkinlik sorumlusuyla görüşülmüş olmalıdır.")
    if contact != ContactOutcome.NONE and not contacted_by.strip():
        errors.append("Görüşmeyi yapan kişiyi belirtin.")
    if len(note.strip()) < MIN_DECISION_NOTE_LENGTH:
        errors.append(
            f"Karar notu en az {MIN_DECISION_NOTE_LENGTH} karakter olmalıdır "
            "(görüşme özeti ve karar gerekçesi)."
        )
    return errors
