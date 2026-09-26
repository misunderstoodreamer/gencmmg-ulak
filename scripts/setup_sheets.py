"""Create the Google Sheets worksheets and seed users declared in secrets.

Usage (from the repository root):

    python scripts/setup_sheets.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # st.secrets resolves .streamlit/secrets.toml relative to the working directory

from core import repository, settings  # noqa: E402


def main() -> int:
    if not settings.sheets_enabled():
        print("Google Sheets is not configured: check [gcp_service_account] and [sheets] in secrets.toml.")
        return 1
    try:
        repository.ensure_schema()
        added = sum(
            repository.add_user_if_missing(u["email"], u["il_kodu"], u["rol"])
            for u in settings.admin_accounts() + settings.seeded_users()
        )
    except repository.RepositoryError as exc:
        print(exc)
        return 1
    print(f"Worksheets ready. {added} user(s) added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
