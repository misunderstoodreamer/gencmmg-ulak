"""Administration: users and integrations."""

import pandas as pd
import streamlit as st

from core import attachments, notifications, repository, settings
from core.auth import require_role
from core.domain import Role, role_label
from core.provinces import province_label
from ui.components import page_header, stat_row

require_role(Role.ADMIN)

page_header(
    "Yönetim paneli",
    subtitle="Kullanıcılar ve sistem bağlantıları.",
    eyebrow="Yönetim",
)

users_tab, system_tab = st.tabs(["Kullanıcılar", "Sistem"])


def _load_users() -> list[dict]:
    users = {u["email"]: u for u in settings.admin_accounts() + settings.seeded_users()}
    if settings.sheets_enabled():
        try:
            for u in repository.list_users():
                users.setdefault(u["email"], u)
        except repository.RepositoryError as exc:
            st.error(f"Kullanıcı listesi okunamadı. {exc}")
    return list(users.values())


with users_tab:
    users = _load_users()
    if not users:
        st.caption("Kayıtlı kullanıcı bulunamadı.")
    else:
        users_df = pd.DataFrame(users).assign(
            rol=lambda d: d["rol"].map(role_label),
            il=lambda d: d["il_kodu"].map(province_label),
        )[["email", "rol", "il"]]
        roles = users_df["rol"].value_counts()
        stat_row([(role, int(count)) for role, count in roles.items()])
        st.space("small")
        st.dataframe(
            users_df.sort_values(["rol", "email"]),
            hide_index=True,
            width="stretch",
            column_config={
                "email": st.column_config.TextColumn("E-posta", width="large"),
                "rol": st.column_config.TextColumn("Rol"),
                "il": st.column_config.TextColumn("İl"),
            },
        )
        st.caption(
            "Yöneticiler secrets dosyasındaki [admin] ve [[admins]] bölümlerinden, "
            "diğer kullanıcılar Kullanici_Rolleri sayfasından okunur."
        )

with system_tab:
    mail_column, sheets_column, drive_column = st.columns(3, gap="medium")

    with mail_column, st.container(border=True, key="panel-mail"):
        st.markdown("**Gmail**")
        if settings.mail_enabled():
            st.badge("Yapılandırıldı", color="green", icon=":material/check_circle:")
        else:
            st.badge("Yapılandırılmadı", color="orange", icon=":material/warning:")
        st.caption("Giriş kodları ve bildirimler bu hesap üzerinden gönderilir.")
        if st.button("Bağlantıyı test et", icon=":material/network_check:"):
            with st.spinner("Gmail'e bağlanılıyor..."):
                ok, message = notifications.check_connection()
            (st.success if ok else st.error)(message)

    with sheets_column, st.container(border=True, key="panel-sheets"):
        st.markdown("**Google Sheets**")
        if settings.sheets_enabled():
            st.badge("Yapılandırıldı", color="green", icon=":material/check_circle:")
        else:
            st.badge("Yapılandırılmadı", color="orange", icon=":material/warning:")
        st.caption("Eksik sayfa ve kolonları oluşturur, secrets dosyasındaki kullanıcıları ekler.")
        if st.button("Tabloları hazırla", icon=":material/table_chart:"):
            try:
                with st.spinner("Tablolar hazırlanıyor..."):
                    repository.ensure_schema()
                    added = sum(
                        repository.add_user_if_missing(u["email"], u["il_kodu"], u["rol"])
                        for u in settings.admin_accounts() + settings.seeded_users()
                    )
                st.success(f"Tablolar hazır. {added} kullanıcı eklendi.")
            except repository.RepositoryError as exc:
                st.error(str(exc))

    with drive_column, st.container(border=True, key="panel-drive"):
        st.markdown("**Google Drive**")
        if settings.attachments_enabled():
            st.badge("Yapılandırıldı", color="green", icon=":material/check_circle:")
        else:
            st.badge("Yapılandırılmadı", color="orange", icon=":material/warning:")
        st.caption("Talep ekleri Apps Script aracılığıyla Drive'a yüklenir. Kurulum: README.")
        if st.button("Drive'ı test et", icon=":material/cloud_done:"):
            with st.spinner("Drive'a bağlanılıyor..."):
                ok, message = attachments.check_connection()
            (st.success if ok else st.error)(message)

    st.space("small")
    with st.container(border=True, key="panel-access"):
        st.markdown("**Erişim matrisi**")
        st.dataframe(
            pd.DataFrame(
                {
                    "Sayfa": ["Yeni talep", "Talepler", "Onay havuzu", "Raporlar", "Yönetim paneli"],
                    Role.BRANCH_PRESIDENT.label: ["Kendi ili", "Kendi ili", "—", "—", "—"],
                    Role.BOARD_MEMBER.label: ["—", "Tüm iller (salt okunur)", "—", "Evet", "—"],
                    Role.ADMIN.label: ["Tüm iller", "Tüm iller", "Evet", "Evet", "Evet"],
                }
            ),
            hide_index=True,
            width="stretch",
        )
