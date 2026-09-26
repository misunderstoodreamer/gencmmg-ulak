"""Sign-in: e-mail one-time code."""

import base64
from html import escape
from pathlib import Path

import streamlit as st

from core import settings
from core.auth import cancel_login, mask_email, pending_login, request_login_code, verify_login_code

_MARK_SVG = (Path(__file__).parents[1] / "assets" / "mark.svg").read_bytes()
BRAND_MARK = (
    f'<img src="data:image/svg+xml;base64,{base64.b64encode(_MARK_SVG).decode()}" '
    'width="40" height="40" alt="">'
)

st.html('<div style="height: 6vh"></div>')
_, center, _ = st.columns([1, 1.15, 1])

with center:
    st.html(
        f'<div class="brand">{BRAND_MARK}<div>'
        '<p class="brand-name">Genç MMG</p>'
        '<p class="brand-tagline">Mimar ve Mühendisler Grubu · Gençlik Komisyonu</p>'
        "</div></div>"
    )

    with st.container(border=True, key="panel-login"):
        pending = pending_login()

        if pending is None:
            st.html(
                '<p class="login-title">Oturum açın</p>'
                '<p class="login-lead">Kayıtlı e-posta adresinize tek kullanımlık bir giriş kodu göndereceğiz.</p>'
            )
            if not settings.mail_enabled():
                st.warning("E-posta gönderimi yapılandırılmadığı için şu an giriş yapılamıyor.")

            with st.form("request_code", border=False):
                email = st.text_input("E-posta adresi", placeholder="ad.soyad@ornek.com", autocomplete="email")
                if st.form_submit_button("Giriş kodu gönder", type="primary", width="stretch"):
                    with st.spinner("Kod gönderiliyor..."):
                        ok, message = request_login_code(email)
                    if ok:
                        st.rerun()
                    st.error(message)
        else:
            st.html(
                '<p class="login-title">Kodu girin</p>'
                f'<p class="login-lead"><strong>{escape(mask_email(pending.user.email))}</strong> adresine '
                "6 haneli bir kod gönderdik.</p>"
            )
            with st.form("verify_code", border=False):
                code = st.text_input("Doğrulama kodu", max_chars=6, placeholder="000000", autocomplete="one-time-code")
                if st.form_submit_button("Doğrula ve devam et", type="primary", width="stretch"):
                    ok, message = verify_login_code(code)
                    if ok:
                        st.rerun()
                    st.error(message)

            if st.button("Farklı bir e-posta kullan", type="tertiary", icon=":material/arrow_back:"):
                cancel_login()
                st.rerun()

    st.html(
        f'<p class="login-foot">Kodlar {settings.otp_expiry_minutes()} dakika geçerlidir. '
        "Erişim sorunları için Genel Merkez ile iletişime geçin.</p>"
    )
