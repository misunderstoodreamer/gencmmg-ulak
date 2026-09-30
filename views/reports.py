"""Headquarters reporting: request statistics and export for board members and admins."""

import altair as alt
import pandas as pd
import streamlit as st

from core.auth import require_role
from core.domain import SLA_HOURS, RequestStatus, Role
from core.provinces import province_label, province_name
from ui.components import empty_state, load_requests, overdue_count, page_header, stat_row, status_counts

require_role(Role.BOARD_MEMBER, Role.ADMIN)

page_header(
    "Raporlar",
    subtitle="Tüm illerin talep istatistikleri ve yanıt süreleri.",
    eyebrow="Genel Merkez",
)

df = load_requests()
counts = status_counts(df)
stat_row(
    [
        ("Toplam talep", len(df)),
        ("Bekleyen", counts[RequestStatus.PENDING]),
        (f"{SLA_HOURS} saati aşan", overdue_count(df)),
        ("Onaylanan", counts[RequestStatus.APPROVED]),
        ("Reddedilen", counts[RequestStatus.REJECTED]),
    ]
)

if df.empty:
    st.space("small")
    empty_state("Henüz talep yok", "İllerden gelen talepler burada raporlanır.")
    st.stop()

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

st.space("small")
with st.container(border=True, key="panel-export"):
    st.markdown("**Talep kayıtları**")
    export = df.assign(il=df["il_kodu"].map(province_label)).sort_values("talep_zamani", ascending=False)
    st.dataframe(export, hide_index=True, width="stretch")
    st.download_button(
        "CSV olarak indir",
        data=export.to_csv(index=False).encode("utf-8-sig"),
        file_name="etkinlik_talepleri.csv",
        mime="text/csv",
        icon=":material/download:",
    )
