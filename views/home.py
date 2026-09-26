"""Landing dashboard, scoped to the signed-in user's role."""

import streamlit as st

from core.auth import current_user
from core.domain import RequestStatus, role_label
from core.provinces import province_name
from ui.components import format_date, load_requests, overdue_count, page_header, stat_row, status_counts

user = current_user()
scope = user.province_scope

page_header(
    "Genel bakış",
    subtitle=f"{role_label(user.role)} · {province_name(user.province) if scope else 'Tüm iller'}",
    eyebrow="Etkinlik Onay Platformu",
)

df = load_requests(scope)
counts = status_counts(df)

if user.can_review:
    stat_row(
        [
            ("Bekleyen", counts[RequestStatus.PENDING]),
            ("48 saati aşan", overdue_count(df)),
            ("Onaylanan", counts[RequestStatus.APPROVED]),
            ("Toplam talep", len(df)),
        ]
    )
else:
    stat_row(
        [
            ("Toplam talep", len(df)),
            ("Bekleyen", counts[RequestStatus.PENDING]),
            ("Onaylanan", counts[RequestStatus.APPROVED]),
            ("Reddedilen", counts[RequestStatus.REJECTED]),
        ]
    )

st.space("medium")
st.subheader("Hızlı erişim")

actions = []
if user.can_submit:
    actions += [
        ("views/new_request.py", "Yeni talep oluştur", "Etkinlik bilgilerini girip Genel Merkez onayına gönderin.", ":material/add_circle:"),
        ("views/request_tracking.py", "Taleplerimi görüntüle", "Gönderilen taleplerin durumunu ve karar notlarını izleyin.", ":material/list_alt:"),
    ]
if user.can_review:
    actions.append(
        ("views/approval_queue.py", "Onay havuzu", "Bekleyen talepleri değerlendirin ve karar verin.", ":material/fact_check:")
    )
if user.is_admin:
    actions.append(
        ("views/admin_panel.py", "Yönetim paneli", "Kullanıcılar, raporlar ve sistem bağlantıları.", ":material/admin_panel_settings:")
    )

for column, (page, title, text, icon) in zip(st.columns(len(actions)), actions):
    with column, st.container(border=True, key=f"card-action-{page.split('/')[-1][:-3]}", height="stretch"):
        st.page_link(page, label=title, icon=icon)
        st.caption(text)

st.space("medium")
st.subheader("Son talepler")

if df.empty:
    st.caption("Henüz talep bulunmuyor.")
else:
    recent = df.sort_values("talep_zamani", ascending=False).head(8)
    table = recent.assign(
        il=recent["il_kodu"].map(province_name),
        tarih=recent["etkinlik_tarihi"].map(format_date),
    )[["etkinlik_id", "etkinlik_adi", "il", "tarih", "durum"]]
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "etkinlik_id": st.column_config.TextColumn("Talep no", width="small"),
            "etkinlik_adi": st.column_config.TextColumn("Etkinlik", width="large"),
            "il": st.column_config.TextColumn("İl"),
            "tarih": st.column_config.TextColumn("Etkinlik tarihi"),
            "durum": st.column_config.TextColumn("Durum"),
        },
    )
