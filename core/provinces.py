"""Provinces that are allowed to submit event requests."""

from __future__ import annotations

PROVINCES: dict[str, str] = {
    "06": "Ankara",
    "35": "İzmir",
    "77": "Yalova",
    "38": "Kayseri",
    "54": "Sakarya",
    "27": "Gaziantep",
    "23": "Elazığ",
    "04": "Ağrı",
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
