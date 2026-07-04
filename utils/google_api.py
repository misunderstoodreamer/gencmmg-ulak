"""Google Sheets (gspread) ve Gmail (smtplib) entegrasyonu."""

from __future__ import annotations

import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from utils.iller import gecerli_il_kodu, il_etiket

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_USERS = "Kullanici_Rolleri"
SHEET_REQUESTS = "Talepler_Havuzu"

USER_HEADERS = ["email", "il_kodu", "rol"]
REQUEST_HEADERS = [
    "etkinlik_id",
    "il_kodu",
    "etkinlik_adi",
    "etkinlik_tarihi",
    "acil_mi",
    "durum",
    "talep_zamani",
    "merkez_aksiyon_zamani",
    "sla_farki_saat",
    "acil_gerekce",
    "temsilci_email",
    "sorumlu_ad_soyad",
    "sorumlu_unvan",
    "etkinlik_yeri",
    "etkinlik_nasil",
    "iletisim_yapildi",
    "iletisim_yapan_kisi",
    "onay_notu",
    "onaylayan_email",
]

_PLACEHOLDER_MARKERS = ("YOUR_", "your-", "CHANGE_ME", "xxx")


def is_sheets_configured() -> bool:
    """Geçerli Google Sheets kimlik bilgisi var mı?"""
    try:
        if st.secrets.get("sheets", {}).get("enabled", True) is False:
            return False
        if "gcp_service_account" not in st.secrets or "sheets" not in st.secrets:
            return False

        pk = str(st.secrets["gcp_service_account"].get("private_key", ""))
        if "BEGIN PRIVATE KEY" not in pk:
            return False
        if any(marker in pk for marker in _PLACEHOLDER_MARKERS):
            return False

        sid = str(st.secrets["sheets"].get("spreadsheet_id", "")).strip()
        if not sid or any(marker in sid for marker in _PLACEHOLDER_MARKERS):
            return False

        return True
    except Exception:
        return False


def sheets_status_banner():
    """Sheets yapılandırılmamışsa kullanıcıya bilgi göster."""
    if not is_sheets_configured():
        st.info(
            "Google Sheets bağlantısı henüz yapılandırılmadı. "
            "Giriş yapabilirsiniz; veri işlemleri için `.streamlit/secrets.toml` "
            "dosyasındaki `gcp_service_account` ve `sheets` bölümlerini doldurun."
        )


def _normalize_private_key(sa_info: dict) -> dict:
    """TOML içindeki \\n kaçışlarını gerçek satır sonuna çevirir."""
    info = dict(sa_info)
    pk = info.get("private_key", "")
    if isinstance(pk, str) and "\\n" in pk:
        info["private_key"] = pk.replace("\\n", "\n")
    return info


def _get_credentials() -> Credentials | None:
    """Streamlit secrets üzerinden service account kimlik bilgisi."""
    if not is_sheets_configured():
        return None
    try:
        sa_info = _normalize_private_key(dict(st.secrets["gcp_service_account"]))
        return Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    except (ValueError, OSError, KeyError):
        return None


def _get_client() -> gspread.Client | None:
    creds = _get_credentials()
    if creds is None:
        return None
    return gspread.authorize(creds)


def _get_spreadsheet():
    if not is_sheets_configured():
        return None
    spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
    client = _get_client()
    if client is None:
        return None
    return client.open_by_key(spreadsheet_id)


def _get_users_from_secrets() -> list[dict]:
    """Sheets yokken secrets.toml içindeki [[users]] kayıtları."""
    users = []
    try:
        for row in st.secrets.get("users", []):
            users.append(
                {
                    "email": str(row["email"]).strip().lower(),
                    "il_kodu": str(row.get("il_kodu", "00")),
                    "rol": str(row["rol"]),
                }
            )
    except Exception:
        pass
    return users


def _sync_worksheet_headers(ws, headers: list[str]) -> None:
    """Mevcut sayfaya eksik kolon başlıklarını ekler."""
    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers)
        return
    missing = [h for h in headers if h not in existing]
    if missing:
        new_headers = existing + missing
        ws.update(range_name=f"A1:{_col_letter(len(new_headers))}1", values=[new_headers])


def _col_letter(n: int) -> str:
    """1-based kolon numarasından Excel harfi (A, B, ... Z, AA)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _ensure_worksheet(name: str, headers: list[str]):
    """Sayfa yoksa oluştur ve başlık satırını yaz."""
    ss = _get_spreadsheet()
    if ss is None:
        return None
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws

    _sync_worksheet_headers(ws, headers)
    return ws


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def _normalize_user(row: dict) -> dict:
    """Sheets/secrets kayıtlarını standart forma çevirir."""
    kod = row.get("il_kodu", "00")
    if kod in (None, ""):
        kod = "00"
    return {
        "email": str(row.get("email", "")).strip().lower(),
        "il_kodu": str(kod).zfill(2),
        "rol": str(row.get("rol", "")).strip(),
    }


def get_user_by_email(email: str) -> dict | None:
    """Kullanici_Rolleri tablosundan veya secrets [[users]] kaydından getir."""
    email_lower = email.strip().lower()

    for row in _get_users_from_secrets():
        if row["email"] == email_lower:
            return _normalize_user(row)

    if not is_sheets_configured():
        return None

    try:
        ws = _ensure_worksheet(SHEET_USERS, USER_HEADERS)
        if ws is None:
            return None
        records = ws.get_all_records()
        for row in records:
            if str(row.get("email", "")).strip().lower() == email_lower:
                return _normalize_user(row)
    except Exception:
        pass
    return None


def ensure_admin_user() -> None:
    """Google Sheets'e admin kullanıcısını ekler (yoksa)."""
    if not is_sheets_configured() or "admin" not in st.secrets:
        return
    admin_email = str(st.secrets["admin"]["email"]).strip().lower()
    il_kodu = str(st.secrets["admin"].get("il_kodu", "00")).zfill(2)
    try:
        ws = _ensure_worksheet(SHEET_USERS, USER_HEADERS)
        if ws is None:
            return
        records = ws.get_all_records()
        for row in records:
            if str(row.get("email", "")).strip().lower() == admin_email:
                return
        ws.append_row([admin_email, il_kodu, "Admin"])
    except Exception:
        pass


def get_all_users() -> list[dict]:
    users = list(_get_users_from_secrets())
    if not is_sheets_configured():
        return users
    try:
        ws = _ensure_worksheet(SHEET_USERS, USER_HEADERS)
        if ws is None:
            return users
        sheet_users = ws.get_all_records()
        seen = {u["email"] for u in users}
        for row in sheet_users:
            email = str(row.get("email", "")).strip().lower()
            if email and email not in seen:
                users.append(row)
                seen.add(email)
    except Exception:
        pass
    return users


def get_requests(il_kodu: str | None = None) -> pd.DataFrame:
    """
    Talepler_Havuzu kayıtlarını getir.
    il_kodu verilirse filtreler; None ise tüm kayıtlar.
    """
    if not is_sheets_configured():
        return pd.DataFrame()

    try:
        ws = _ensure_worksheet(SHEET_REQUESTS, REQUEST_HEADERS)
        if ws is None:
            return pd.DataFrame()
        records = ws.get_all_records()
        df = _records_to_df(records)
        if df.empty:
            return df

        if il_kodu is not None:
            kod = str(il_kodu).zfill(2)
            df = df[df["il_kodu"].astype(str).str.zfill(2) == kod]

        return df
    except Exception:
        return pd.DataFrame()


def _find_row_index(ws, etkinlik_id: str) -> int | None:
    """1-based satır indeksi (başlık hariç değil, sheet satır numarası)."""
    cell = ws.find(str(etkinlik_id), in_column=1)
    if cell:
        return cell.row
    return None


def create_request(
    il_kodu: str,
    etkinlik_adi: str,
    etkinlik_tarihi: datetime,
    acil_mi: bool,
    acil_gerekce: str,
    temsilci_email: str,
    sorumlu_ad_soyad: str,
    sorumlu_unvan: str,
    etkinlik_yeri: str,
    etkinlik_nasil: str,
) -> tuple[bool, str]:
    """Yeni etkinlik talebi oluştur ve merkeze bildirim gönder."""
    if not gecerli_il_kodu(il_kodu):
        return False, "Geçersiz il. Yalnızca tanımlı önemli iller için talep oluşturulabilir."

    if not is_sheets_configured():
        return False, (
            "Google Sheets yapılandırılmadı. "
            "Lütfen secrets.toml dosyasına geçerli service account anahtarını ekleyin."
        )

    ws = _ensure_worksheet(SHEET_REQUESTS, REQUEST_HEADERS)
    if ws is None:
        return False, "Google Sheets bağlantısı kurulamadı."

    etkinlik_id = f"ETK-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tarih_str = etkinlik_tarihi.strftime("%Y-%m-%d")

    row = [
        etkinlik_id,
        str(il_kodu).zfill(2),
        etkinlik_adi.strip(),
        tarih_str,
        str(acil_mi),
        "Bekliyor",
        now,
        "",
        "",
        acil_gerekce.strip() if acil_mi else "",
        temsilci_email.strip().lower(),
        sorumlu_ad_soyad.strip(),
        sorumlu_unvan.strip(),
        etkinlik_yeri.strip(),
        etkinlik_nasil.strip(),
        "",
        "",
        "",
        "",
    ]

    try:
        ws.append_row(row)
        send_new_request_notification(
            etkinlik_id=etkinlik_id,
            il_kodu=str(il_kodu).zfill(2),
            etkinlik_adi=etkinlik_adi,
            etkinlik_tarihi=tarih_str,
            acil_mi=acil_mi,
            temsilci_email=temsilci_email,
            sorumlu_ad_soyad=sorumlu_ad_soyad,
            sorumlu_unvan=sorumlu_unvan,
            etkinlik_yeri=etkinlik_yeri,
            etkinlik_nasil=etkinlik_nasil,
        )
        return True, f"Talep başarıyla oluşturuldu. ID: {etkinlik_id}"
    except Exception as exc:
        return False, f"Talep kaydedilemedi: {exc}"


def update_request_status(
    etkinlik_id: str,
    yeni_durum: str,
    temsilci_email: str,
    etkinlik_adi: str,
    iletisim_yapildi: str,
    iletisim_yapan_kisi: str,
    onay_notu: str,
    onaylayan_email: str,
) -> tuple[bool, str]:
    """Merkez onay/red işlemi — SLA hesaplar ve il temsilcisine bildirim gönderir."""
    if not is_sheets_configured():
        return False, "Google Sheets yapılandırılmadı."

    ws = _ensure_worksheet(SHEET_REQUESTS, REQUEST_HEADERS)
    if ws is None:
        return False, "Google Sheets bağlantısı kurulamadı."
    row_idx = _find_row_index(ws, etkinlik_id)
    if not row_idx:
        return False, "Talep bulunamadı."

    headers = ws.row_values(1)
    row_data = dict(zip(headers, ws.row_values(row_idx)))

    talep_zamani_str = row_data.get("talep_zamani", "")
    try:
        talep_zamani = datetime.strptime(talep_zamani_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        talep_zamani = datetime.now()

    aksiyon_zamani = datetime.now()
    sla_farki = round((aksiyon_zamani - talep_zamani).total_seconds() / 3600, 2)

    col_map = {h: i + 1 for i, h in enumerate(headers)}
    ws.update_cell(row_idx, col_map.get("durum", 6), yeni_durum)
    ws.update_cell(
        row_idx,
        col_map.get("merkez_aksiyon_zamani", 8),
        aksiyon_zamani.strftime("%Y-%m-%d %H:%M:%S"),
    )
    ws.update_cell(row_idx, col_map.get("sla_farki_saat", 9), str(sla_farki))

    for field, value in (
        ("iletisim_yapildi", iletisim_yapildi),
        ("iletisim_yapan_kisi", iletisim_yapan_kisi),
        ("onay_notu", onay_notu),
        ("onaylayan_email", onaylayan_email),
    ):
        if field in col_map:
            ws.update_cell(row_idx, col_map[field], value)

    send_status_notification(
        temsilci_email=temsilci_email or row_data.get("temsilci_email", ""),
        etkinlik_id=etkinlik_id,
        etkinlik_adi=etkinlik_adi or row_data.get("etkinlik_adi", ""),
        durum=yeni_durum,
        sla_farki_saat=sla_farki,
        onay_notu=onay_notu,
    )

    return True, f"Talep '{yeni_durum}' olarak güncellendi. SLA: {sla_farki} saat"


def validate_14_day_rule(etkinlik_tarihi: datetime, acil_mi: bool) -> tuple[bool, str]:
    """14 gün kuralı doğrulaması."""
    min_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=14
    )
    event_date = etkinlik_tarihi.replace(hour=0, minute=0, second=0, microsecond=0)

    if event_date < min_date and not acil_mi:
        return (
            False,
            "Etkinlik tarihi bugünden itibaren en az 14 gün sonrası olmalıdır. "
            "Acil etkinlik ise 'Acil Etkinlik' kutusunu işaretleyin ve gerekçe girin.",
        )
    return True, ""


def is_email_configured() -> bool:
    """Gmail App Password yapılandırılmış mı?"""
    try:
        sender = str(st.secrets["email"]["sender"])
        password = str(st.secrets["email"]["app_password"])
        if any(marker in sender for marker in _PLACEHOLDER_MARKERS):
            return False
        if any(marker in password for marker in _PLACEHOLDER_MARKERS):
            return False
        return bool(sender and password)
    except (KeyError, TypeError):
        return False


def setup_google_sheets() -> tuple[bool, str]:
    """
    Google Sheets tablolarını oluşturur ve varsayılan kullanıcıları yükler.
    secrets.toml'da sheets.enabled=true ve geçerli kimlik bilgisi gerekir.
    """
    if not is_sheets_configured():
        return False, (
            "Google Sheets yapılandırılmamış. secrets.toml içinde "
            "gcp_service_account, sheets.spreadsheet_id ve sheets.enabled=true ayarlayın."
        )

    try:
        _ensure_worksheet(SHEET_USERS, USER_HEADERS)
        _ensure_worksheet(SHEET_REQUESTS, REQUEST_HEADERS)
        ensure_admin_user()

        for row in _get_users_from_secrets():
            email = row["email"]
            il_kodu = str(row.get("il_kodu", "00")).zfill(2)
            rol = row.get("rol", "")
            if email and rol:
                _upsert_user(email, il_kodu, rol)

        return True, (
            "Google Sheets tabloları hazır: Kullanici_Rolleri ve Talepler_Havuzu. "
            "Varsayılan kullanıcılar eklendi."
        )
    except Exception as exc:
        return False, f"Kurulum hatası: {exc}"


def _upsert_user(email: str, il_kodu: str, rol: str) -> None:
    ws = _ensure_worksheet(SHEET_USERS, USER_HEADERS)
    if ws is None:
        return
    email = email.strip().lower()
    records = ws.get_all_records()
    for row in records:
        if str(row.get("email", "")).strip().lower() == email:
            return
    ws.append_row([email, il_kodu, rol])


def hours_since_request(talep_zamani_str: str) -> float:
    """Talep zamanından bu yana geçen saat."""
    if not talep_zamani_str:
        return 0.0
    try:
        talep_zamani = datetime.strptime(str(talep_zamani_str), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return 0.0
    return (datetime.now() - talep_zamani).total_seconds() / 3600


def _send_email(to_email: str, subject: str, html_body: str, *, quiet: bool = False) -> bool:
    """Gmail App Password ile senkron e-posta gönderimi."""
    if not to_email:
        return False

    try:
        sender = str(st.secrets["email"]["sender"]).strip()
        password = str(st.secrets["email"]["app_password"]).replace(" ", "").strip()
        if any(marker in str(sender) for marker in _PLACEHOLDER_MARKERS):
            return False
        if any(marker in str(password) for marker in _PLACEHOLDER_MARKERS):
            return False
    except (KeyError, TypeError):
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # Önce 465 SSL, olmazsa 587 STARTTLS dene
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
                server.login(sender, password)
                server.sendmail(sender, to_email, msg.as_string())
            return True
        except smtplib.SMTPAuthenticationError:
            raise
        except Exception:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender, password)
                server.sendmail(sender, to_email, msg.as_string())
            return True
    except smtplib.SMTPAuthenticationError:
        if not quiet:
            st.error(
                "Gmail App Password reddedildi. "
                "https://myaccount.google.com/apppasswords adresinden yeni şifre oluşturun."
            )
        return False
    except Exception as exc:
        if not quiet:
            st.warning(f"E-posta gönderilemedi ({to_email}): {exc}")
        return False


def test_gmail_connection() -> tuple[bool, str]:
    """Admin paneli için Gmail bağlantı testi."""
    try:
        sender = str(st.secrets["email"]["sender"]).strip()
        password = str(st.secrets["email"]["app_password"]).replace(" ", "").strip()
    except (KeyError, TypeError):
        return False, "secrets.toml [email] bölümü eksik."

    if not is_email_configured():
        return False, "Gmail App Password yapılandırılmamış."

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender, password)
        return True, f"Gmail bağlantısı başarılı ({sender})"
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail kullanıcı adı/şifre kabul edilmedi. "
            "Yeni App Password oluşturun: myaccount.google.com/apppasswords"
        )
    except Exception as exc:
        return False, str(exc)


def send_otp_email(email: str, otp_code: str) -> bool:
    """Giriş için 6 haneli doğrulama kodu gönder."""
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color: #1d1d1f;">Giriş Doğrulama Kodu</h2>
        <p>Genç MMG Etkinlik Onay Platformu giriş kodunuz:</p>
        <p style="font-size: 2rem; font-weight: 700; letter-spacing: 8px; color: #2563eb;">
            {otp_code}
        </p>
        <p style="color: #64748b;">Bu kod 10 dakika geçerlidir. Kimseyle paylaşmayın.</p>
    </div>
    """
    return _send_email(email, "[MMG] Giriş Doğrulama Kodu", html, quiet=True)


def send_new_request_notification(
    etkinlik_id: str,
    il_kodu: str,
    etkinlik_adi: str,
    etkinlik_tarihi: str,
    acil_mi: bool,
    temsilci_email: str,
    sorumlu_ad_soyad: str = "",
    sorumlu_unvan: str = "",
    etkinlik_yeri: str = "",
    etkinlik_nasil: str = "",
) -> None:
    """Yeni talep oluşturulduğunda merkeze bildirim."""
    merkez_email = st.secrets["email"]["merkez_email"]
    acil_label = "🔴 ACİL" if acil_mi else "Normal"

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto;">
        <h2 style="color: #1d1d1f;">Yeni Etkinlik Talebi</h2>
        <p><strong>ID:</strong> {etkinlik_id}</p>
        <p><strong>İl:</strong> {il_etiket(il_kodu)}</p>
        <p><strong>Etkinlik:</strong> {etkinlik_adi}</p>
        <p><strong>Tarih:</strong> {etkinlik_tarihi}</p>
        <p><strong>Öncelik:</strong> {acil_label}</p>
        <p><strong>Temsilci:</strong> {temsilci_email}</p>
        <hr>
        <h3 style="font-size:1rem;color:#334155;">Referans Sorumlu</h3>
        <p><strong>Ad Soyad:</strong> {sorumlu_ad_soyad}</p>
        <p><strong>Unvan:</strong> {sorumlu_unvan}</p>
        <h3 style="font-size:1rem;color:#334155;">Etkinlik Detayı</h3>
        <p><strong>Nerede:</strong> {etkinlik_yeri}</p>
        <p><strong>Nasıl:</strong> {etkinlik_nasil}</p>
        <p style="color: #86868b;">Genç MMG Etkinlik Onay Platformu</p>
    </div>
    """
    _send_email(merkez_email, f"[MMG] Yeni Talep: {etkinlik_adi}", html)


def send_status_notification(
    temsilci_email: str,
    etkinlik_id: str,
    etkinlik_adi: str,
    durum: str,
    sla_farki_saat: float,
    onay_notu: str = "",
) -> None:
    """Merkez onay/red sonrası il temsilcisine bildirim."""
    renk = "#34c759" if durum == "Onaylandı" else "#ff3b30"
    not_html = f"<p><strong>Merkez Notu:</strong> {onay_notu}</p>" if onay_notu else ""

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto;">
        <h2 style="color: {renk};">Talep {durum}</h2>
        <p><strong>ID:</strong> {etkinlik_id}</p>
        <p><strong>Etkinlik:</strong> {etkinlik_adi}</p>
        <p><strong>SLA Süresi:</strong> {sla_farki_saat} saat</p>
        {not_html}
        <p style="color: #86868b;">Genç MMG Etkinlik Onay Platformu</p>
    </div>
    """
    _send_email(
        temsilci_email,
        f"[MMG] Talep {durum}: {etkinlik_adi}",
        html,
    )
