"""Administration: reporting, users and integrations."""

import altair as alt
import pandas as pd
import streamlit as st

from core import attachments, notifications, repository, settings
from core.auth import require_role
from core.domain import RequestStatus, Role, role_label
from core.provinces import province_label, province_name
from ui.components import load_requests, overdue_count, page_header, stat_row, status_counts

require_role(Role.ADMIN)

page_header(
    "Yönetim paneli",
    subtitle="Raporlar, kullanıcılar ve sistem bağlantıları.",
    eyebrow="Yönetim",
)

overview_tab, requests_tab, users_tab, system_tab = st.tabs(
    ["Genel bakış", "Talepler", "Kullanıcılar", "Sistem"]
)


def _load_users() -> list[dict]:
    users = {u["email"]: u for u in settings.admin_accounts() + settings.seeded_users()}
    if settings.sheets_enabled():
        try:
            for u in repository.list_users():
                users.setdefault(u["email"], u)
        except repository.RepositoryError as exc:
            st.error(f"Kullanıcı listesi okunamadı. {exc}")
    return list(users.values())


with overview_tab:
    df = load_requests()
    counts = status_counts(df)
    stat_row(
        [
            ("Toplam talep", len(df)),
            ("Bekleyen", counts[RequestStatus.PENDING]),
            ("48 saati aşan", overdue_count(df)),
            ("Onaylanan", counts[RequestStatus.APPROVED]),
            ("Reddedilen", counts[RequestStatus.REJECTED]),
        ]
    )

    if not df.empty:
        st.space("small")
        chart_column, sla_column = st.columns([2, 1], gap="large")
        with chart_column, st.container(border=True, key="panel-provinces"):
            st.markdown("**İllere göre talep sayısı**")
            by_province = (
                df.groupby("il_kodu").size().rename("Talep").reset_index()
                .assign(İl=lambda d: d["il_kodu"].map(province_name))
            )
            base = alt.Chart(by_province).encode(
                y=alt.Y("İl:N", sort="-x", title=None,
                        axis=alt.Axis(domain=False, ticks=False, labelPadding=10, labelColor="#475569")),
                x=alt.X("Talep:Q", axis=None),
            )
            bars = base.mark_bar(color="#1d4ed8", cornerRadiusEnd=4, height=14).encode(
                tooltip=[alt.Tooltip("İl:N"), alt.Tooltip("Talep:Q", title="Talep sayısı")]
            )
            labels = base.mark_text(align="left", dx=6, color="#334155", fontSize=12).encode(text="Talep:Q")
            st.altair_chart(
                (bars + labels)
                .properties(height=34 * len(by_province), background="transparent")
                .configure_view(stroke=None),
                width="stretch",
                theme=None,
            )
        with sla_column, st.container(border=True, key="panel-sla"):
            st.markdown("**Yanıt süresi**")
            decided = pd.to_numeric(df["sla_farki_saat"], errors="coerce").dropna()
            if decided.empty:
                st.caption("Henüz sonuçlanan talep yok.")
            else:
                for label, value in (("Ortalama", decided.mean()), ("Medyan", decided.median())):
                    st.html(
                        f'<div class="figure"><p class="figure-value">{value:.1f} saat</p>'
                        f'<p class="figure-label">{label}</p></div>'
                    )
                st.caption(f"{len(decided)} sonuçlanan talep üzerinden.")

with requests_tab:
    df = load_requests()
    if df.empty:
        st.caption("Henüz talep kaydı yok.")
    else:
        export = df.assign(il=df["il_kodu"].map(province_label)).sort_values("talep_zamani", ascending=False)
        st.dataframe(export, hide_index=True, width="stretch")
        st.download_button(
            "CSV olarak indir",
            data=export.to_csv(index=False).encode("utf-8-sig"),
            file_name="etkinlik_talepleri.csv",
            mime="text/csv",
            icon=":material/download:",
        )

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
                    "Sayfa": ["Yeni talep", "Taleplerim", "Onay havuzu", "Yönetim paneli"],
                    Role.PROVINCE_REP.label: ["Evet", "Kendi ili", "—", "—"],
                    Role.APPROVER.label: ["—", "—", "Evet", "—"],
                    Role.ADMIN.label: ["Evet", "Tüm iller", "Evet", "Evet"],
                }
            ),
            hide_index=True,
            width="stretch",
        )
