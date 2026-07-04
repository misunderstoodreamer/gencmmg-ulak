"""Önemli iller listesi ve yardımcı fonksiyonlar."""

ILLER = [
    {"kod": "06", "ad": "Ankara"},
    {"kod": "35", "ad": "İzmir"},
    {"kod": "77", "ad": "Yalova"},
    {"kod": "38", "ad": "Kayseri"},
    {"kod": "54", "ad": "Sakarya"},
    {"kod": "27", "ad": "Gaziantep"},
    {"kod": "23", "ad": "Elazığ"},
    {"kod": "04", "ad": "Ağrı"},
]

IL_KODLARI = {il["kod"] for il in ILLER}
IL_ADLARI = {il["kod"]: il["ad"] for il in ILLER}


def il_etiket(kod: str) -> str:
    """06 → '06 — Ankara'"""
    kod = str(kod).zfill(2)
    ad = IL_ADLARI.get(kod)
    return f"{kod} — {ad}" if ad else kod


def il_secenekleri(tumu: bool = False) -> list[str]:
    """Selectbox için etiket listesi."""
    secenekler = [il_etiket(il["kod"]) for il in ILLER]
    if tumu:
        return ["Tümü"] + secenekler
    return secenekler


def etiketten_kod(secim: str) -> str | None:
    """'06 — Ankara' → '06'. 'Tümü' → None."""
    if secim == "Tümü":
        return None
    if " — " in secim:
        return secim.split(" — ", 1)[0].zfill(2)
    return str(secim).zfill(2)


def gecerli_il_kodu(kod: str) -> bool:
    return str(kod).zfill(2) in IL_KODLARI


def varsayilan_il_kodu() -> str:
    return ILLER[0]["kod"]
