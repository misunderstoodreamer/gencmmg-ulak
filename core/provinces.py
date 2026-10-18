"""Provinces that are allowed to submit event requests."""

from __future__ import annotations

# Ordered by plate code; this order is used in every province list.
PROVINCES: dict[str, str] = {
    "04": "Ağrı",
    "06": "Ankara",
    "07": "Antalya",
    "23": "Elazığ",
    "27": "Gaziantep",
    "33": "Mersin",
    "34": "İstanbul",
    "35": "İzmir",
    "38": "Kayseri",
    "42": "Konya",
    "54": "Sakarya",
    "77": "Yalova",
}


def normalize_code(code: object) -> str:
    return str(code).strip().zfill(2)


def is_valid_province(code: object) -> bool:
    return normalize_code(code) in PROVINCES


def province_name(code: object) -> str:
    code = normalize_code(code)
    if code == "00":
        return "Genel Merkez"
    return PROVINCES.get(code, code)


def province_label(code: object) -> str:
    code = normalize_code(code)
    name = province_name(code)
    return f"{name} ({code})" if name != code else code


def province_names_summary() -> str:
    return ", ".join(PROVINCES.values())
