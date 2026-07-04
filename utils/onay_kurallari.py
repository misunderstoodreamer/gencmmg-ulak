"""Onay ekranı kuralları ve doğrulama."""

import html

ILETISIM_BEN = "Evet — Ben etkinlik sorumlusuyla iletişime geçtim"
ILETISIM_BASKA = "Evet — Başka bir kişi iletişime geçti"
ILETISIM_HAYIR = "Hayır — Henüz iletişim kurulmadı"

ILETISIM_SECENEKLERI = [ILETISIM_BEN, ILETISIM_BASKA, ILETISIM_HAYIR]


def validate_onay_form(
    iletisim_durumu: str,
    iletisim_yapan_kisi: str,
    onay_notu: str,
    yeni_durum: str,
) -> list[str]:
    hatalar = []
    if not onay_notu or len(onay_notu.strip()) < 15:
        hatalar.append("Onay/red notu en az 15 karakter olmalıdır (iletişim özeti ve karar gerekçesi).")

    if yeni_durum == "Onaylandı":
        if iletisim_durumu == ILETISIM_HAYIR:
            hatalar.append(
                "Onay için etkinlik sorumlusuyla iletişim kurulmuş olmalıdır. "
                "Önce arayıp görüşün, ardından onaylayın."
            )
        if iletisim_durumu == ILETISIM_BASKA and not iletisim_yapan_kisi.strip():
            hatalar.append("İletişime geçen kişinin adını belirtin.")
        if iletisim_durumu == ILETISIM_BEN and not iletisim_yapan_kisi.strip():
            hatalar.append("İletişim yapan kişi bilgisi eksik.")

    if iletisim_durumu == ILETISIM_BASKA and not iletisim_yapan_kisi.strip():
        hatalar.append("Başka biri iletişime geçtiyse ad soyad zorunludur.")

    return hatalar


def iletisim_ozet_markdown(row) -> str:
    """Tamamlanmış talepler için onay özeti (düz metin markdown)."""
    iletisim = str(row.get("iletisim_yapildi", "") or "").strip()
    yapan = str(row.get("iletisim_yapan_kisi", "") or "").strip()
    notu = str(row.get("onay_notu", "") or "").strip()
    onaylayan = str(row.get("onaylayan_email", "") or "").strip()

    if not iletisim and not notu:
        return ""

    lines = ["**Onay süreci**"]
    if iletisim:
        lines.append(f"- **İletişim:** {html.escape(iletisim)}")
    if yapan:
        lines.append(f"- **İletişim yapan:** {html.escape(yapan)}")
    if notu:
        lines.append(f"- **Not:** {html.escape(notu)}")
    if onaylayan:
        lines.append(f"- **İşlemi yapan:** {html.escape(onaylayan)}")
    return "\n".join(lines)
