"""Transactional e-mail over Gmail SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from core import attachments, settings
from core.domain import RequestStatus
from core.provinces import province_label

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_TIMEOUT_SECONDS = 20
BRAND = "Genç MMG Etkinlik Onay Platformu"


class MailError(RuntimeError):
    pass


def _login(server: smtplib.SMTP, mail: settings.MailSettings) -> None:
    server.login(mail.sender, mail.app_password)


def send(to: str, subject: str, html_body: str) -> None:
    """Send an HTML e-mail. Raises MailError on failure."""
    mail = settings.mail_settings()
    if mail is None:
        raise MailError("E-posta gönderimi yapılandırılmamış.")
    if not to:
        raise MailError("Alıcı adresi boş.")

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"Genç MMG <{mail.sender}>"
    message["To"] = to
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        try:
            with smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=SMTP_TIMEOUT_SECONDS) as server:
                _login(server, mail)
                server.sendmail(mail.sender, to, message.as_string())
        except smtplib.SMTPAuthenticationError:
            raise
        except (OSError, smtplib.SMTPException):
            with smtplib.SMTP(SMTP_HOST, 587, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.starttls()
                _login(server, mail)
                server.sendmail(mail.sender, to, message.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        log.error("Gmail rejected the app password")
        raise MailError("Gmail uygulama şifresi reddedildi.") from exc
    except (OSError, smtplib.SMTPException) as exc:
        log.exception("Mail to %s failed", to)
        raise MailError(f"E-posta gönderilemedi: {exc}") from exc


def check_connection() -> tuple[bool, str]:
    mail = settings.mail_settings()
    if mail is None:
        return False, "E-posta ayarları eksik veya örnek değerlerle dolu."
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=SMTP_TIMEOUT_SECONDS) as server:
            _login(server, mail)
        return True, f"Gmail bağlantısı başarılı ({mail.sender})."
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail uygulama şifresi reddedildi. myaccount.google.com/apppasswords üzerinden yenileyin."
    except (OSError, smtplib.SMTPException) as exc:
        return False, f"Bağlantı kurulamadı: {exc}"


# --- Templates -------------------------------------------------------------


def _layout(title: str, rows: list[tuple[str, str]], intro: str = "", accent: str = "#1d4ed8") -> str:
    body_rows = "".join(
        f'<tr><td style="padding:6px 0;color:#64748b;width:160px;vertical-align:top">{escape(k)}</td>'
        f'<td style="padding:6px 0;color:#0f172a">{escape(str(v) or "-")}</td></tr>'
        for k, v in rows
    )
    intro_html = f'<p style="margin:0 0 16px;color:#334155">{escape(intro)}</p>' if intro else ""
    return f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px">
      <div style="background:#ffffff;border:1px solid #e2e8f0;border-top:4px solid {accent};border-radius:10px;padding:24px">
        <h2 style="margin:0 0 12px;font-size:18px;color:#0f172a">{escape(title)}</h2>
        {intro_html}
        <table style="border-collapse:collapse;width:100%;font-size:14px">{body_rows}</table>
      </div>
      <p style="margin:16px 0 0;color:#94a3b8;font-size:12px;text-align:center">{BRAND}</p>
    </div>
    """


def send_login_code(to: str, code: str, expiry_minutes: int) -> None:
    html_body = f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px">
      <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:28px;text-align:center">
        <p style="margin:0 0 8px;color:#64748b;font-size:14px">Giriş doğrulama kodunuz</p>
        <p style="margin:0;font-size:32px;font-weight:700;letter-spacing:8px;color:#0f172a">{escape(code)}</p>
        <p style="margin:16px 0 0;color:#64748b;font-size:13px">
          Kod {expiry_minutes} dakika geçerlidir. Bu kodu kimseyle paylaşmayın.
        </p>
      </div>
      <p style="margin:16px 0 0;color:#94a3b8;font-size:12px;text-align:center">{BRAND}</p>
    </div>
    """
    send(to, "Genç MMG giriş kodu", html_body)


def send_new_request_notice(record: dict) -> None:
    mail = settings.mail_settings()
    if mail is None:
        return
    urgent = str(record.get("acil_mi")) == "True"
    rows = [
        ("Talep no", record["etkinlik_id"]),
        ("İl", province_label(record["il_kodu"])),
        ("Etkinlik", record["etkinlik_adi"]),
        ("Tarih", record["etkinlik_tarihi"]),
        ("Öncelik", "Acil" if urgent else "Normal"),
        ("Talebi açan", record["temsilci_email"]),
        ("Sorumlu", f'{record["sorumlu_ad_soyad"]} — {record["sorumlu_unvan"]}'),
        ("Yer", record["etkinlik_yeri"]),
        ("Plan", record["etkinlik_nasil"]),
    ]
    if urgent:
        rows.append(("Acil gerekçesi", record["acil_gerekce"]))
    files = attachments.parse(record.get("ek_dosyalar"))
    rows.append(
        ("Ekler", ", ".join(f.name for f in files) if files else f'Eklenmedi — {record.get("ek_dosya_yok_gerekce", "")}')
    )
    prefix = "[Acil] " if urgent else ""
    send(
        mail.headquarters_email,
        f"{prefix}Yeni etkinlik talebi: {record['etkinlik_adi']}",
        _layout("Yeni etkinlik talebi", rows, accent="#dc2626" if urgent else "#1d4ed8"),
    )


def send_decision_notice(record: dict) -> None:
    status = record["durum"]
    approved = status == RequestStatus.APPROVED
    rows = [
        ("Talep no", record["etkinlik_id"]),
        ("Etkinlik", record["etkinlik_adi"]),
        ("Karar", status),
        ("Yanıt süresi", f'{record["sla_farki_saat"]} saat'),
        ("Merkez notu", record.get("onay_notu", "")),
    ]
    send(
        record["temsilci_email"],
        f"Talebiniz {status.lower()}: {record['etkinlik_adi']}",
        _layout(
            f"Talebiniz {status.lower()}",
            rows,
            intro="Etkinlik talebiniz Genel Merkez tarafından değerlendirildi.",
            accent="#16a34a" if approved else "#dc2626",
        ),
    )
