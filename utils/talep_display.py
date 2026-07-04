"""Talep detaylarını görüntüleme yardımcıları."""

import html

import streamlit as st

from utils.iller import il_etiket


def _esc(text) -> str:
    return html.escape(str(text or ""))


def _val(row, key: str, default: str = "—") -> str:
    v = row.get(key, "")
    return str(v).strip() if v not in (None, "", "nan") else default


def render_talep_karti(
    row,
    *,
    show_il: bool = False,
    sla_hours: float | None = None,
    durum: str | None = None,
    onay_ozet_html: str = "",
):
    """Onay/takip sayfalarında düzgün görünen talep kartı (HTML sanitization sorunu yok)."""
    etkinlik_id = _val(row, "etkinlik_id")
    etkinlik_adi = _val(row, "etkinlik_adi")
    durum = durum or _val(row, "durum")

    acil = str(row.get("acil_mi", "")).lower() in ("true", "1", "evet")
    bekliyor = durum == "Bekliyor"

    with st.container(border=True):
        h1, h2 = st.columns([5, 1])
        with h1:
            if acil:
                st.markdown("🔴 **ACİL**")
            st.markdown(f"### {etkinlik_adi}")
        with h2:
            if bekliyor and sla_hours is not None and sla_hours >= 48:
                st.error(f"⚠ {int(sla_hours)}s")

        st.markdown(f"**ID:** `{etkinlik_id}`")
        if show_il:
            st.markdown(f"**İl:** {il_etiket(_val(row, 'il_kodu', ''))}")
        st.markdown(f"**Temsilci:** {_esc(row.get('temsilci_email', '—'))}")
        st.markdown(f"**Etkinlik Tarihi:** {_esc(_val(row, 'etkinlik_tarihi'))}")

        st.markdown("---")
        st.markdown("**Referans sorumlu**")
        st.markdown(f"- **Ad Soyad:** {_esc(_val(row, 'sorumlu_ad_soyad'))}")
        st.markdown(f"- **Unvan:** {_esc(_val(row, 'sorumlu_unvan'))}")

        st.markdown("**Etkinlik detayı**")
        st.markdown(f"- **Nerede:** {_esc(_val(row, 'etkinlik_yeri'))}")
        st.markdown(f"- **Nasıl:** {_esc(_val(row, 'etkinlik_nasil'))}")

        if _val(row, "acil_gerekce") != "—":
            st.markdown(f"- **Acil gerekçe:** {_esc(_val(row, 'acil_gerekce'))}")

        st.markdown(f"**Talep zamanı:** {_esc(_val(row, 'talep_zamani'))}")
        st.markdown(f"**Durum:** **{durum}**")

        if onay_ozet_html:
            st.markdown("---")
            st.markdown(onay_ozet_html, unsafe_allow_html=True)


def validate_talep_detaylari(
    sorumlu_ad_soyad: str,
    sorumlu_unvan: str,
    etkinlik_yeri: str,
    etkinlik_nasil: str,
) -> list[str]:
    hatalar = []
    if not sorumlu_ad_soyad.strip():
        hatalar.append("Sorumlu kişi ad soyad zorunludur.")
    if not sorumlu_unvan.strip():
        hatalar.append("Sorumlu kişi unvanı zorunludur.")
    if not etkinlik_yeri.strip():
        hatalar.append("Etkinliğin yapılacağı yer zorunludur.")
    if not etkinlik_nasil.strip():
        hatalar.append("Etkinliğin nasıl yapılacağı zorunludur.")
    if len(etkinlik_nasil.strip()) < 20:
        hatalar.append("Nasıl yapılacak alanı en az 20 karakter olmalıdır.")
    return hatalar
