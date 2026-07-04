"""Admin Paneli — Tüm veriler, kullanıcılar ve sistem özeti"""

import streamlit as st

from utils.auth import ROLE_ADMIN, init_session_state, render_user_sidebar, require_role
from utils.google_api import (
    ensure_admin_user,
    get_all_users,
    get_requests,
    hours_since_request,
    is_email_configured,
    is_sheets_configured,
    setup_google_sheets,
    sheets_status_banner,
    test_gmail_connection,
)
from utils.iller import ILLER, il_etiket
from utils.ui_styles import apply_apple_style, glass_header, hide_sidebar_pages_for_role, set_sidebar_visible

st.set_page_config(
    page_title="Admin Panel | Genç MMG",
    page_icon="🛡️",
    layout="wide",
)

apply_apple_style()
init_session_state()
require_role([ROLE_ADMIN])
set_sidebar_visible(True)
hide_sidebar_pages_for_role(st.session_state.rol)
render_user_sidebar()

from utils.google_api import is_sheets_configured, sheets_status_banner

if not is_sheets_configured():
    sheets_status_banner()

glass_header(
    "Admin Paneli",
    "Önemli iller: Ankara, İzmir, Yalova, Kayseri, Sakarya, Gaziantep, Elazığ, Ağrı",
)

tab_ozet, tab_talepler, tab_kullanicilar, tab_ayarlar = st.tabs(
    ["Özet", "Tüm Talepler", "Kullanıcılar", "Sistem"]
)

# --- Özet ---
with tab_ozet:
    try:
        ensure_admin_user()
    except Exception:
        pass

    df = get_requests()
    users = get_all_users()

    bekleyen = len(df[df["durum"] == "Bekliyor"]) if not df.empty else 0
    sla_asan = 0
    if not df.empty:
        bekleyen_df = df[df["durum"] == "Bekliyor"]
        sla_asan = sum(
            1
            for _, r in bekleyen_df.iterrows()
            if hours_since_request(str(r.get("talep_zamani", ""))) >= 48
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Talep", len(df))
    c2.metric("Bekleyen", bekleyen)
    c3.metric("SLA Aşan", sla_asan)
    c4.metric("Kullanıcı", len(users))
    c5.metric("Aktif İl", len(ILLER))

    st.markdown("##### Tanımlı İller")
    il_listesi = ", ".join(f"**{il['ad']}** ({il['kod']})" for il in ILLER)
    st.markdown(il_listesi)

    st.markdown("##### Hızlı Gezinme")
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        st.page_link("pages/1_📝_Yeni_Talep.py", label="Yeni Talep", icon="📝")
    with nav2:
        st.page_link("pages/2_🔎_Talep_Takip.py", label="Talep Takibi", icon="🔎")
    with nav3:
        st.page_link("pages/3_✅_Merkez_Onay.py", label="Merkez Onay", icon="✅")

    if not df.empty:
        st.markdown("##### İllere Göre Talep Dağılımı")
        il_dagilim = (
            df.groupby(df["il_kodu"].astype(str).str.zfill(2))
            .size()
            .reset_index(name="adet")
        )
        il_dagilim["İl"] = il_dagilim["il_kodu"].apply(il_etiket)
        il_dagilim = il_dagilim.sort_values("adet", ascending=False)
        st.bar_chart(il_dagilim.set_index("İl"))

        st.markdown("##### Durum Dağılımı")
        durum_dagilim = df["durum"].value_counts().reset_index()
        durum_dagilim.columns = ["Durum", "Adet"]
        st.dataframe(durum_dagilim, use_container_width=True, hide_index=True)

# --- Tüm Talepler ---
with tab_talepler:
    df = get_requests()
    if df.empty:
        st.info("Henüz talep kaydı yok.")
    else:
        goster_df = df.copy()
        goster_df["il"] = goster_df["il_kodu"].astype(str).apply(il_etiket)
        st.dataframe(
            goster_df.sort_values("talep_zamani", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
        csv = goster_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "CSV İndir",
            data=csv,
            file_name="talepler_havuzu.csv",
            mime="text/csv",
        )

# --- Kullanıcılar ---
with tab_kullanicilar:
    users = get_all_users()
    if not users:
        st.info("Kullanıcı kaydı bulunamadı veya Sheets bağlantısı yapılandırılmamış.")
        st.markdown(
            """
            <div class="ui-card ui-card-muted">
                <p>Admin hesabı <code>secrets.toml</code> üzerinden tanımlıdır:</p>
                <p><strong>admin@gencmmg.org</strong> — Rol: Admin</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        import pandas as pd

        users_df = pd.DataFrame(users)
        st.dataframe(users_df, use_container_width=True, hide_index=True)

        rol_sayim = users_df["rol"].value_counts().reset_index()
        rol_sayim.columns = ["Rol", "Adet"]
        st.markdown("##### Rol Dağılımı")
        st.dataframe(rol_sayim, use_container_width=True, hide_index=True)

# --- Sistem ---
with tab_ayarlar:
    st.markdown("##### Google Bağlantıları")

    c_mail, c_sheet = st.columns(2)
    c_mail.metric("Gmail OTP", "Aktif" if is_email_configured() else "Kapalı")
    c_sheet.metric("Google Sheets", "Aktif" if is_sheets_configured() else "Kapalı")

    if st.button("Gmail Bağlantısını Test Et"):
        ok, msg = test_gmail_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.markdown(
        """
        **Kurulum adımları:**
        1. Google Cloud'da Service Account oluşturun, JSON anahtarını indirin
        2. Google Sheets dosyası oluşturup service account e-postasına düzenleme yetkisi verin
        3. `secrets.toml` → `gcp_service_account`, `sheets.spreadsheet_id`, `sheets.enabled=true`
        4. Gmail App Password → `[email]` bölümü
        5. Aşağıdaki butonla tabloları oluşturun
        """
    )

    if st.button("Google Sheets Tablolarını Oluştur / Güncelle", type="primary"):
        ok, msg = setup_google_sheets()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.markdown("---")
    st.markdown("##### Aktif Oturum")
    st.json(
        {
            "email": st.session_state.email,
            "rol": st.session_state.rol,
            "il": il_etiket(st.session_state.il_kodu),
        }
    )

    st.markdown("##### Sayfa Erişim Matrisi")
    st.markdown(
        """
        | Sayfa | Il_Temsilcisi | Merkez_Onayci | Admin |
        |-------|:-------------:|:-------------:|:-----:|
        | Yeni Talep | ✅ | — | ✅ |
        | Talep Takip | ✅ (kendi ili) | — | ✅ (tümü) |
        | Merkez Onay | — | ✅ | ✅ |
        | Admin Panel | — | — | ✅ |
        """
    )

    st.markdown("##### secrets.toml Admin Bloğu")
    st.code(
        """[admin]
email = "admin@gencmmg.org"
il_kodu = "00"
""",
        language="toml",
    )
