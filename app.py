"""Genç MMG Etkinlik Onay Platformu — Giriş Ekranı"""

import streamlit as st

from utils.auth import (
    ROLE_ADMIN,
    ROLE_IL_TEMSILCISI,
    ROLE_MERKEZ,
    cancel_otp_flow,
    init_session_state,
    is_admin,
    logout,
    render_user_sidebar,
    request_login_otp,
    verify_login_otp,
)
from utils.google_api import ensure_admin_user, is_email_configured, is_sheets_configured
from utils.iller import il_etiket
from utils.ui_styles import (
    apply_apple_style,
    glass_header,
    hide_sidebar_pages_for_role,
    set_sidebar_visible,
)

init_session_state()
authenticated = bool(st.session_state.get("authenticated"))

st.set_page_config(
    page_title="Genç MMG | Giriş",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded" if authenticated else "collapsed",
)

apply_apple_style()

if authenticated:
    set_sidebar_visible(True)
    hide_sidebar_pages_for_role(st.session_state.rol)
    render_user_sidebar()
else:
    set_sidebar_visible(False)

glass_header(
    "Genç MMG Etkinlik Onay Platformu",
    "Mimar ve Mühendisler Grubu Gençlik Komisyonu",
)

if authenticated:
    rol = st.session_state.rol
    il_kodu = st.session_state.il_kodu

    if is_admin():
        st.markdown(
            '<span class="badge badge-admin">Admin — Tam Erişim</span>',
            unsafe_allow_html=True,
        )

    st.success(f"Oturum açık: **{st.session_state.email}**")

    col_info, col_nav = st.columns([1, 2])
    with col_info:
        st.markdown(
            f"""
            <div class="ui-card ui-card-muted">
                <h3>Hesap Bilgileri</h3>
                <p><strong>Rol:</strong> {rol}</p>
                <p><strong>İl:</strong> {il_etiket(il_kodu)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_nav:
        st.markdown("##### Hızlı Erişim")
        if rol in (ROLE_IL_TEMSILCISI, ROLE_ADMIN):
            st.page_link("pages/1_📝_Yeni_Talep.py", label="Yeni Talep Oluştur", icon="📝")
            st.page_link("pages/2_🔎_Talep_Takip.py", label="Talep Takibi", icon="🔎")
        if rol in (ROLE_MERKEZ, ROLE_ADMIN):
            st.page_link("pages/3_✅_Merkez_Onay.py", label="Merkez Onay Havuzu", icon="✅")
        if rol == ROLE_ADMIN:
            st.page_link("pages/4_🛡️_Admin_Panel.py", label="Admin Paneli", icon="🛡️")

    if st.button("Çıkış Yap"):
        logout()
        st.rerun()

else:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        if st.session_state.get("login_step") == "otp":
            mail_ok = st.session_state.get("otp_mail_sent")
            if mail_ok:
                st.success(f"Kod **{st.session_state.otp_email}** adresine gönderildi.")
            else:
                st.warning(
                    "Gmail şu an mail gönderemiyor (App Password sorunu). "
                    "Kodu aşağıdan girin — e-posta beklemeden giriş yapabilirsiniz."
                )

            kod = st.session_state.get("otp_dev_code") or st.session_state.get("otp_code")
            if kod:
                st.markdown(
                    f"""
                    <div style="background:#eff6ff;border:2px solid #2563eb;border-radius:12px;
                    padding:1.25rem;text-align:center;margin:1rem 0;">
                    <p style="margin:0;color:#64748b;font-size:0.9rem;">Giriş kodunuz</p>
                    <p style="margin:0.25rem 0;font-size:2.5rem;font-weight:700;
                    letter-spacing:10px;color:#1d4ed8;">{kod}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.form("otp_form"):
                otp = st.text_input(
                    "6 Haneli Kod",
                    max_chars=6,
                    placeholder="000000",
                )
                col_v, col_c = st.columns(2)
                verify_btn = col_v.form_submit_button("Doğrula", use_container_width=True)
                cancel_btn = col_c.form_submit_button("İptal", use_container_width=True)

                if verify_btn:
                    ok, msg = verify_login_otp(otp)
                    if ok:
                        ensure_admin_user()
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                if cancel_btn:
                    cancel_otp_flow()
                    st.rerun()
        else:
            st.markdown(
                """
                <div class="ui-card">
                    <h3>Giriş Yap</h3>
                    <p>Kayıtlı e-postanıza 6 haneli doğrulama kodu gönderilir.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("email_form"):
                email = st.text_input("E-posta Adresi", placeholder="cagataygmr@gmail.com")
                submitted = st.form_submit_button("Doğrulama Kodu Gönder", use_container_width=True)

                if submitted:
                    ok, msg = request_login_otp(email)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with col_right:
        mail_durum = "✅ Yapılandırıldı" if is_email_configured() else "⚠️ Yapılandırılmadı"
        sheets_durum = "✅ Bağlı" if is_sheets_configured() else "⚠️ Kapalı"

        st.markdown(
            f"""
            <div class="ui-card ui-card-muted">
                <h3>Giriş Kuralları</h3>
                <p>1. E-postanız sistem listesinde olmalı</p>
                <p>2. Gmail ile 6 haneli kod gönderilir</p>
                <p>3. Kod 10 dakika geçerlidir</p>
                <hr style="border:none;border-top:1px solid #e2e8f0;margin:1rem 0;">
                <p><strong>Gmail:</strong> {mail_durum}</p>
                <p><strong>Google Sheets:</strong> {sheets_durum}</p>
                <p style="color:#64748b;font-size:0.85rem;">
                    Test: <code>admin@gencmmg.org</code> — secrets.toml [auth] otp_dev_mode
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
