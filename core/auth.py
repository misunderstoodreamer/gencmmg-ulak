"""Session handling, e-mail OTP login and role-based access."""

from __future__ import annotations

import hmac
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import streamlit as st

from core import notifications, repository, settings
from core.domain import Role
from core.provinces import normalize_code

log = logging.getLogger(__name__)

OTP_MAX_ATTEMPTS = 5
_USER_KEY = "auth_user"
_PENDING_KEY = "auth_pending_login"


@dataclass(frozen=True)
class SessionUser:
    email: str
    province: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def can_submit(self) -> bool:
        return self.role in (Role.PROVINCE_REP, Role.ADMIN)

    @property
    def can_review(self) -> bool:
        return self.role in (Role.APPROVER, Role.ADMIN)

    @property
    def province_scope(self) -> str | None:
        """Province filter for listings; None means all provinces."""
        return None if self.can_review else self.province


@dataclass
class PendingLogin:
    user: SessionUser
    code: str
    expires_at: datetime
    attempts: int = field(default=0)


def current_user() -> SessionUser | None:
    return st.session_state.get(_USER_KEY)


def pending_login() -> PendingLogin | None:
    return st.session_state.get(_PENDING_KEY)


def _lookup(email: str) -> SessionUser | None:
    accounts = settings.admin_accounts() + settings.seeded_users()
    record = next((a for a in accounts if a["email"] == email), None)
    if record is None and settings.sheets_enabled():
        record = repository.find_user(email)
    if record is None:
        return None
    return SessionUser(
        email=record["email"],
        province=normalize_code(record["il_kodu"]),
        role=record["rol"],
    )


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    masked = f"{local[:1]}•••" if len(local) <= 2 else f"{local[0]}•••{local[-1]}"
    return f"{masked}@{domain}"


def request_login_code(email: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if "@" not in email:
        return False, "Geçerli bir e-posta adresi girin."
    if not settings.mail_enabled():
        return False, "E-posta gönderimi yapılandırılmamış. Lütfen yöneticiye başvurun."

    try:
        user = _lookup(email)
    except repository.RepositoryError:
        return False, "Kullanıcı listesine şu an erişilemiyor. Lütfen biraz sonra tekrar deneyin."
    if user is None:
        return False, "Bu e-posta adresi sistemde kayıtlı değil."

    code = f"{secrets.randbelow(1_000_000):06d}"
    expiry = settings.otp_expiry_minutes()
    try:
        notifications.send_login_code(email, code, expiry)
    except notifications.MailError:
        return False, "Doğrulama kodu gönderilemedi. Lütfen biraz sonra tekrar deneyin."

    st.session_state[_PENDING_KEY] = PendingLogin(
        user=user,
        code=code,
        expires_at=datetime.now() + timedelta(minutes=expiry),
    )
    return True, f"Doğrulama kodu {mask_email(email)} adresine gönderildi."


def verify_login_code(code: str) -> tuple[bool, str]:
    pending = pending_login()
    if pending is None:
        return False, "Önce e-posta adresinizi girip kod isteyin."

    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        return False, "6 haneli doğrulama kodunu girin."

    if datetime.now() > pending.expires_at:
        cancel_login()
        return False, "Kodun süresi doldu. Lütfen yeni kod isteyin."

    if not hmac.compare_digest(code, pending.code):
        pending.attempts += 1
        remaining = OTP_MAX_ATTEMPTS - pending.attempts
        if remaining <= 0:
            cancel_login()
            return False, "Çok fazla hatalı deneme. Lütfen yeni kod isteyin."
        return False, f"Kod hatalı. Kalan deneme hakkı: {remaining}."

    st.session_state[_USER_KEY] = pending.user
    cancel_login()
    log.info("User signed in: %s", pending.user.email)
    return True, ""


def cancel_login() -> None:
    st.session_state.pop(_PENDING_KEY, None)


def logout() -> None:
    st.session_state.pop(_USER_KEY, None)
    cancel_login()


def require_role(*roles: Role) -> SessionUser:
    """Stop rendering unless the signed-in user holds one of the given roles."""
    user = current_user()
    if user is None or user.role not in roles:
        st.error("Bu sayfaya erişim yetkiniz bulunmuyor.")
        st.stop()
    return user
