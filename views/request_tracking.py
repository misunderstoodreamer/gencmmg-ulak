"""Track requests: own province for branch presidents, all provinces for headquarters."""

import streamlit as st

from core.auth import require_role
from core.domain import RequestStatus, Role
from core.provinces import PROVINCES, province_label, province_name
from ui.components import empty_state, load_requests, page_header, request_card, status_counts

ALL = "all"

user = require_role(Role.BRANCH_PRESIDENT, Role.BOARD_MEMBER, Role.ADMIN)

page_header(
    "Tüm talepler" if user.can_view_all else "Taleplerim",
    subtitle="Tüm iller" if user.can_view_all else f"{province_name(user.province)} iline ait etkinlik talepleri",
    eyebrow="Talepler",
)

filters = st.container(horizontal=True, vertical_alignment="center", gap="medium")

province = user.province_scope
if user.can_view_all:
    with filters:
        province = st.selectbox(
            "İl",
            options=[ALL, *PROVINCES],
            format_func=lambda code: "Tüm iller" if code == ALL else province_label(code),
            width=240,
            label_visibility="collapsed",
        )
    province = None if province == ALL else province

df = load_requests(province)

if df.empty:
    empty_state(
        "Henüz talep yok",
        "İllerden gelen talepler burada listelenir." if user.can_view_all else "Oluşturduğunuz talepler burada listelenir.",
    )
    st.stop()

counts = status_counts(df)
with filters:
    status = st.segmented_control(
        "Durum",
        options=[ALL, *RequestStatus],
        format_func=lambda s: f"Tümü  {len(df)}" if s == ALL else f"{s}  {counts[s]}",
        default=ALL,
        required=True,
        label_visibility="collapsed",
    )

visible = df if status == ALL else df[df["durum"] == status]
visible = visible.sort_values("talep_zamani", ascending=False)

st.space("small")
if visible.empty:
    empty_state("Bu durumda talep yok")
for _, row in visible.iterrows():
    request_card(row, show_province=user.can_view_all)

with st.expander("Tablo görünümü", icon=":material/table_view:"):
    st.dataframe(visible, hide_index=True, width="stretch")
