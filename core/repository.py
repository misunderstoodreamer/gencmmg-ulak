"""Google Sheets persistence for users and event requests."""

from __future__ import annotations

import logging

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from core import settings
from core.domain import REQUEST_COLUMNS, REQUESTS_SHEET, USER_COLUMNS, USERS_SHEET
from core.provinces import normalize_code

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
READ_CACHE_TTL_SECONDS = 30


class RepositoryError(RuntimeError):
    """Raised when Google Sheets is unavailable or misconfigured."""


@st.cache_resource(show_spinner=False)
def _spreadsheet() -> gspread.Spreadsheet:
    info = settings.service_account_info()
    sheet_id = settings.spreadsheet_id()
    if info is None or sheet_id is None:
        raise RepositoryError("Google Sheets yapılandırılmamış.")
    credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(credentials).open_by_key(sheet_id)


@st.cache_resource(show_spinner=False)
def _worksheet(name: str, columns: tuple[str, ...]) -> gspread.Worksheet:
    """Open a worksheet, creating it or appending missing header columns once per process."""
    spreadsheet = _spreadsheet()
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(columns))
        ws.append_row(list(columns))
        return ws

    header = ws.row_values(1)
    missing = [c for c in columns if c not in header]
    if not header:
        ws.append_row(list(columns))
    elif missing:
        full = header + missing
        ws.update(range_name=f"A1:{rowcol_to_a1(1, len(full))}", values=[full])
    return ws


def _users_ws() -> gspread.Worksheet:
    return _worksheet(USERS_SHEET, tuple(USER_COLUMNS))


def _requests_ws() -> gspread.Worksheet:
    return _worksheet(REQUESTS_SHEET, tuple(REQUEST_COLUMNS))


def _call(action: str, fn, *args, **kwargs):
    if not settings.sheets_enabled():
        raise RepositoryError("Google Sheets yapılandırılmamış.")
    try:
        return fn(*args, **kwargs)
    except RepositoryError:
        raise
    except Exception as exc:
        log.exception("Sheets %s failed", action)
        raise RepositoryError(f"Google Sheets işlemi başarısız ({action}): {exc}") from exc


def ensure_schema() -> None:
    _call("schema", lambda: (_users_ws(), _requests_ws()))


# --- Users -----------------------------------------------------------------


@st.cache_data(ttl=READ_CACHE_TTL_SECONDS, show_spinner=False)
def _user_records() -> list[dict]:
    return _call("read users", lambda: _users_ws().get_all_records())


def list_users() -> list[dict]:
    users = []
    for row in _user_records():
        email = str(row.get("email", "")).strip().lower()
        if email:
            users.append(
                {
                    "email": email,
                    "il_kodu": normalize_code(row.get("il_kodu") or "00"),
                    "rol": str(row.get("rol", "")).strip(),
                }
            )
    return users


def find_user(email: str) -> dict | None:
    email = email.strip().lower()
    return next((u for u in list_users() if u["email"] == email), None)


def add_user_if_missing(email: str, province: str, role: str) -> bool:
    email = email.strip().lower()
    if find_user(email):
        return False
    _call("add user", lambda: _users_ws().append_row([email, normalize_code(province), role]))
    _user_records.clear()
    return True


# --- Requests --------------------------------------------------------------


@st.cache_data(ttl=READ_CACHE_TTL_SECONDS, show_spinner=False)
def _request_records() -> list[dict]:
    return _call("read requests", lambda: _requests_ws().get_all_records())


def list_requests(province: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(_request_records())
    if df.empty:
        return pd.DataFrame(columns=REQUEST_COLUMNS)
    for column in REQUEST_COLUMNS:
        if column not in df:
            df[column] = ""
    # Sheets auto-types numeric-looking cells; keep every column as text.
    df = df.astype(str)
    df["il_kodu"] = df["il_kodu"].map(normalize_code)
    if province is not None:
        df = df[df["il_kodu"] == normalize_code(province)]
    return df


def append_request(record: dict) -> None:
    def _append():
        ws = _requests_ws()
        # Follow the sheet's actual column order; columns may have been appended over time.
        row = [record.get(column, "") for column in ws.row_values(1)]
        ws.append_row(row, value_input_option="RAW")

    _call("append request", _append)
    _request_records.clear()


def get_request(request_id: str) -> tuple[int, dict] | None:
    """Fresh (uncached) read of a single request. Returns (sheet_row, record)."""

    def _read():
        ws = _requests_ws()
        cell = ws.find(str(request_id), in_column=1)
        if cell is None:
            return None
        header = ws.row_values(1)
        values = ws.row_values(cell.row)
        return cell.row, dict(zip(header, values + [""] * (len(header) - len(values))))

    return _call("read request", _read)


def update_request(sheet_row: int, fields: dict) -> None:
    def _write():
        ws = _requests_ws()
        header = ws.row_values(1)
        updates = [
            {"range": rowcol_to_a1(sheet_row, header.index(k) + 1), "values": [[v]]}
            for k, v in fields.items()
            if k in header
        ]
        ws.batch_update(updates, value_input_option="RAW")

    _call("update request", _write)
    _request_records.clear()
