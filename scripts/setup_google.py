"""
Google Sheets tablolarını oluşturur.
Kullanım: streamlit secrets yüklü ortamda veya secrets.toml ile birlikte çalıştırın.

  cd E:\\projects\\genc-mmg-etkinlik-onay
  python scripts/setup_google.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

# secrets.toml yükle (streamlit dışında çalıştırma için)
secrets_path = ROOT / ".streamlit" / "secrets.toml"
if secrets_path.exists() and not hasattr(st, "_secrets"):
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    with open(secrets_path, "rb") as f:
        st.secrets = tomllib.load(f)  # type: ignore

from utils.google_api import setup_google_sheets, is_sheets_configured

if __name__ == "__main__":
    if not is_sheets_configured():
        print("HATA: secrets.toml içinde Google Sheets yapılandırması eksik.")
        print("sheets.enabled=true ve geçerli service account anahtarı gerekli.")
        sys.exit(1)

    ok, msg = setup_google_sheets()
    print(msg)
    sys.exit(0 if ok else 1)
