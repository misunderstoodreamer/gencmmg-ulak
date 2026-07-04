"""Oturum yönetimi, OTP girişi ve rol bazlı erişim kontrolü."""

import random
from datetime import datetime, timedelta

import streamlit as st

from utils.google_api import get_user_by_email, is_email_configured, send_otp_email
from utils.iller import il_etiket

ROLE_IL_TEMSILCISI = "Il_Temsilcisi"
ROLE_MERKEZ = "Merkez_Onayci"
ROLE_ADMIN = "Admin"

OTP_EXPIRE_MINUTES = 10


def init_session_state():
    """Varsayılan session state değerlerini başlat."""
    defaults = {
        "authenticated": False,
        "email": None,
        "il_kodu": None,
        "rol": None,
        "login_step": "email",
        "otp_email": None,
        "otp_code": None,
        "otp_expires": None,
        "otp_user": None,
        "otp_dev_code": None,
        "otp_mail_sent": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _admin_from_secrets(email: str) -> dict | None:
    """secrets.toml içindeki admin hesapları."""
    email = email.strip().lower()

    if "admin" in st.secrets:
        admin_email = str(st.secrets["admin"].get("email", "")).strip().lower()
        if email == admin_email:
            return {
                "email": admin_email,
                "il_kodu": str(st.secrets["admin"].get("il_kodu", "00")).zfill(2),
                "rol": ROLE_ADMIN,
            }

    try:
        for admin in st.secrets.get("admins", []):
            adm_email = str(admin.get("email", "")).strip().lower()
            if email == adm_email:
                return {
                    "email": adm_email,
                    "il_kodu": str(admin.get("il_kodu", "00")).zfill(2),
                    "rol": ROLE_ADMIN,
                }
    except Exception:
        pass

    return None


def _resolve_user(email: str) -> dict | None:
    email = email.strip().lower()
    user = _admin_from_secrets(email)
    if not user:
        user = get_user_by_email(email)
    return user


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked = local[0] + "***"
    else:
        masked = local[0] + "***" + local[-1]
    return f"{masked}@{domain}"


def request_login_otp(email: str) -> tuple[bool, str]:
    """Kayıtlı e-postaya 6 haneli doğrulama kodu gönder."""
    email = email.strip().lower()
    if not email:
        return False, "Lütfen geçerli bir e-posta adresi girin."

    user = _resolve_user(email)
    if not user:
        return False, "Bu e-posta adresi sistemde kayıtlı değil."

    otp = f"{random.randint(0, 999999):06d}"
    expires = datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)

    st.session_state.login_step = "otp"
    st.session_state.otp_email = email
    st.session_state.otp_code = otp
    st.session_state.otp_expires = expires
    st.session_state.otp_user = user
    st.session_state.otp_dev_code = otp
    st.session_state.otp_mail_sent = False

    dev_mode = bool(st.secrets.get("auth", {}).get("otp_dev_mode", False))

    if is_email_configured():
        st.session_state.otp_mail_sent = send_otp_email(email, otp)

    if st.session_state.otp_mail_sent:
        st.session_state.otp_dev_code = None
        return True, f"Doğrulama kodu {_mask_email(email)} adresine gönderildi."

    # Mail gitmese bile dev modda veya yedek olarak ekranda kod göster
    return (
        True,
        f"E-posta şu an gönderilemiyor. Aşağıdaki 6 haneli kodu kullanın: **{otp}**",
    )


def verify_login_otp(code: str) -> tuple[bool, str]:
    """6 haneli kodu doğrula ve oturumu aç."""
    code = code.strip()
    if not code or len(code) != 6 or not code.isdigit():
        return False, "6 haneli doğrulama kodunu girin."

    if st.session_state.get("login_step") != "otp":
        return False, "Önce e-posta adresinizi girip kod isteyin."

    if datetime.now() > st.session_state.get("otp_expires", datetime.min):
        cancel_otp_flow()
        return False, "Doğrulama kodunun süresi doldu. Lütfen yeniden kod isteyin."

    if code != st.session_state.get("otp_code"):
        return False, "Doğrulama kodu hatalı."

    user = st.session_state.get("otp_user") or {}
    email = st.session_state.get("otp_email", "")

    st.session_state.authenticated = True
    st.session_state.email = email
    st.session_state.il_kodu = str(user.get("il_kodu", "00")).zfill(2)
    st.session_state.rol = user.get("rol", "")

    cancel_otp_flow()
    return True, f"Hoş geldiniz! Rol: {st.session_state.rol}"


def cancel_otp_flow():
    """OTP akışını sıfırla (oturum açık değilken)."""
    st.session_state.login_step = "email"
    st.session_state.otp_email = None
    st.session_state.otp_code = None
    st.session_state.otp_expires = None
    st.session_state.otp_user = None
    st.session_state.otp_dev_code = None


def logout():
    """Oturumu kapat."""
    for key in (
        "authenticated", "email", "il_kodu", "rol",
        "login_step", "otp_email", "otp_code", "otp_expires", "otp_user", "otp_dev_code", "otp_mail_sent",
    ):
        if key == "authenticated":
            st.session_state[key] = False
        elif key == "login_step":
            st.session_state[key] = "email"
        else:
            st.session_state[key] = None


def is_admin() -> bool:
    return st.session_state.get("rol") == ROLE_ADMIN


def can_view_all_requests() -> bool:
    return st.session_state.get("rol") in (ROLE_MERKEZ, ROLE_ADMIN)


def can_approve_requests() -> bool:
    return st.session_state.get("rol") in (ROLE_MERKEZ, ROLE_ADMIN)


def can_create_requests() -> bool:
    return st.session_state.get("rol") in (ROLE_IL_TEMSILCISI, ROLE_ADMIN)


def get_request_il_filter() -> str | None:
    if can_view_all_requests():
        return None
    return st.session_state.il_kodu


def require_auth():
    from utils.ui_styles import set_sidebar_visible

    init_session_state()
    if not st.session_state.get("authenticated"):
        set_sidebar_visible(False)
        st.warning("Bu sayfaya erişmek için önce giriş yapmalısınız.")
        st.page_link("app.py", label="Giriş sayfasına dön", icon="🔐")
        st.stop()


def require_role(allowed_roles: list[str]):
    require_auth()
    if st.session_state.rol not in allowed_roles:
        st.error("Bu sayfaya erişim yetkiniz bulunmuyor.")
        st.page_link("app.py", label="Ana sayfaya dön", icon="🏠")
        st.stop()


def render_user_sidebar():
    if st.session_state.get("authenticated"):
        st.sidebar.markdown("---")
        rol = st.session_state.rol
        badge = " 🛡️" if rol == ROLE_ADMIN else ""
        st.sidebar.markdown(f"**{st.session_state.email}**{badge}")
        st.sidebar.caption(f"İl: {il_etiket(st.session_state.il_kodu)} · Rol: {rol}")
        if st.sidebar.button("Çıkış Yap", use_container_width=True):
            logout()
            st.rerun()
