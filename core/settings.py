"""Typed access to Streamlit secrets."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from core.domain import HEADQUARTERS_PROVINCE, Role

_PLACEHOLDER_MARKERS = ("YOUR_", "your-", "CHANGE_ME", "xxx")


@dataclass(frozen=True)
class MailSettings:
    sender: str
    app_password: str
    headquarters_email: str


def _section(name: str) -> dict:
    try:
        return dict(st.secrets.get(name, {}))
    except Exception:
        return {}


def _is_placeholder(value: str) -> bool:
    return not value or any(marker in value for marker in _PLACEHOLDER_MARKERS)


def service_account_info() -> dict | None:
    info = _section("gcp_service_account")
    key = str(info.get("private_key", ""))
    if "BEGIN PRIVATE KEY" not in key or _is_placeholder(key):
        return None
    # TOML may carry literal "\n" sequences instead of newlines.
    info["private_key"] = key.replace("\\n", "\n")
    return info


def spreadsheet_id() -> str | None:
    sheets = _section("sheets")
    if sheets.get("enabled", True) is False:
        return None
    value = str(sheets.get("spreadsheet_id", "")).strip()
    return None if _is_placeholder(value) else value


def sheets_enabled() -> bool:
    return service_account_info() is not None and spreadsheet_id() is not None


def mail_settings() -> MailSettings | None:
    email = _section("email")
    sender = str(email.get("sender", "")).strip()
    password = str(email.get("app_password", "")).replace(" ", "").strip()
    if _is_placeholder(sender) or _is_placeholder(password):
        return None
    return MailSettings(
        sender=sender,
        app_password=password,
        headquarters_email=str(email.get("merkez_email", sender)).strip(),
    )


def mail_enabled() -> bool:
    return mail_settings() is not None


def _normalize_account(entry: dict, default_role: str | None = None) -> dict | None:
    email = str(entry.get("email", "")).strip().lower()
    role = str(entry.get("rol", default_role or "")).strip()
    if not email or not role:
        return None
    province = str(entry.get("il_kodu") or HEADQUARTERS_PROVINCE).zfill(2)
    return {"email": email, "il_kodu": province, "rol": role}


def admin_accounts() -> list[dict]:
    """Admins declared in secrets via [admin] and [[admins]]."""
    entries = []
    if admin := _section("admin"):
        entries.append(admin)
    try:
        entries.extend(dict(a) for a in st.secrets.get("admins", []))
    except Exception:
        pass
    accounts = (_normalize_account(e, Role.ADMIN) for e in entries)
    return [a for a in accounts if a]


def seeded_users() -> list[dict]:
    """Users declared in secrets via [[users]]."""
    try:
        entries = [dict(u) for u in st.secrets.get("users", [])]
    except Exception:
        return []
    accounts = (_normalize_account(e) for e in entries)
    return [a for a in accounts if a]


@dataclass(frozen=True)
class UploadSettings:
    url: str
    token: str


def upload_settings() -> UploadSettings | None:
    """Apps Script web app that stores attachments (see scripts/apps_script/Code.gs)."""
    drive = _section("drive")
    url = str(drive.get("upload_url", "")).strip()
    token = str(drive.get("upload_token", "")).strip()
    if _is_placeholder(url) or _is_placeholder(token) or not url.startswith("https://"):
        return None
    return UploadSettings(url=url, token=token)


def attachments_enabled() -> bool:
    return upload_settings() is not None


def otp_expiry_minutes() -> int:
    return int(_section("auth").get("otp_expire_minutes", 10))
