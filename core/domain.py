"""Domain constants.

String values are persisted in Google Sheets; changing them breaks existing rows.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    PROVINCE_REP = "Il_Temsilcisi"
    APPROVER = "Merkez_Onayci"
    ADMIN = "Admin"

    @property
    def label(self) -> str:
        return _ROLE_LABELS[self]


_ROLE_LABELS = {
    Role.PROVINCE_REP: "İl Temsilcisi",
    Role.APPROVER: "Merkez Onaycı",
    Role.ADMIN: "Yönetici",
}


def role_label(value: str | None) -> str:
    try:
        return Role(value).label
    except ValueError:
        return value or "-"


class RequestStatus(StrEnum):
    PENDING = "Bekliyor"
    APPROVED = "Onaylandı"
    REJECTED = "Reddedildi"


class ContactOutcome(StrEnum):
    SELF = "Evet — Ben etkinlik sorumlusuyla iletişime geçtim"
    OTHER = "Evet — Başka bir kişi iletişime geçti"
    NONE = "Hayır — Henüz iletişim kurulmadı"


CONTACT_OUTCOME_LABELS = {
    ContactOutcome.SELF: "Sorumluyla ben görüştüm",
    ContactOutcome.OTHER: "Başka bir kişi görüştü",
    ContactOutcome.NONE: "Henüz görüşülmedi",
}


# Worksheet schema
USERS_SHEET = "Kullanici_Rolleri"
REQUESTS_SHEET = "Talepler_Havuzu"

USER_COLUMNS = ["email", "il_kodu", "rol"]
REQUEST_COLUMNS = [
    "etkinlik_id",
    "il_kodu",
    "etkinlik_adi",
    "etkinlik_tarihi",
    "acil_mi",
    "durum",
    "talep_zamani",
    "merkez_aksiyon_zamani",
    "sla_farki_saat",
    "acil_gerekce",
    "temsilci_email",
    "sorumlu_ad_soyad",
    "sorumlu_unvan",
    "etkinlik_yeri",
    "etkinlik_nasil",
    "iletisim_yapildi",
    "iletisim_yapan_kisi",
    "onay_notu",
    "onaylayan_email",
    "ek_dosyalar",
    "ek_dosya_yok_gerekce",
]

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "%d.%m.%Y"
DISPLAY_TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M"

HEADQUARTERS_PROVINCE = "00"
MIN_LEAD_DAYS = 14
SLA_HOURS = 48

ATTACHMENT_MAX_FILES = 5
ATTACHMENT_MAX_MB = 10
ATTACHMENT_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "png", "jpg", "jpeg"]
