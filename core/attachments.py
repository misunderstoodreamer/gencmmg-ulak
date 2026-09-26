"""Request attachments stored in Google Drive via an Apps Script web app.

Service accounts have no Drive storage quota, so they cannot own uploads. Instead a
small Apps Script (scripts/apps_script/Code.gs), deployed from the account that should
own the files, stores them and returns shareable links.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from streamlit.runtime.uploaded_file_manager import UploadedFile

from core import settings

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 120
_SEPARATOR = " | "


class AttachmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class Attachment:
    name: str
    url: str


def serialize(attachments: list[Attachment]) -> str:
    """One `name | url` pair per line, readable directly in the sheet."""
    return "\n".join(f"{a.name}{_SEPARATOR}{a.url}" for a in attachments)


def parse(value: object) -> list[Attachment]:
    attachments = []
    for line in str(value or "").splitlines():
        name, sep, url = line.strip().rpartition(_SEPARATOR)
        if sep and url.startswith("https://"):
            attachments.append(Attachment(name=name, url=url))
    return attachments


def _call(action: str, **payload) -> dict:
    config = settings.upload_settings()
    if config is None:
        raise AttachmentError("Dosya yükleme yapılandırılmamış.")

    body = json.dumps({"action": action, "token": config.token, **payload}).encode("utf-8")
    request = urllib.request.Request(
        config.url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        # Apps Script answers with a redirect to the result; urllib follows it as GET.
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        log.exception("Upload service %s failed", action)
        raise AttachmentError(f"Dosya servisine ulaşılamadı: {exc}") from exc

    if not result.get("ok"):
        error = result.get("error", "bilinmeyen hata")
        log.error("Upload service %s rejected: %s", action, error)
        if error == "unauthorized":
            raise AttachmentError("Dosya servisi anahtarı (upload_token) geçersiz.")
        raise AttachmentError(f"Dosya servisi isteği reddetti: {error}")
    return result


def upload(request_id: str, files: list[UploadedFile]) -> list[Attachment]:
    """Upload files and return view links. All-or-nothing."""
    uploaded: list[str] = []
    attachments = []
    try:
        for file in files:
            result = _call(
                "upload",
                name=f"{request_id} - {file.name}",
                mimeType=file.type or "application/octet-stream",
                data=base64.b64encode(file.getvalue()).decode("ascii"),
            )
            uploaded.append(result["id"])
            attachments.append(Attachment(name=file.name, url=result["url"]))
    except AttachmentError:
        for file_id in uploaded:
            try:
                _call("delete", id=file_id)
            except AttachmentError:
                log.warning("Could not roll back Drive file %s", file_id)
        raise
    return attachments


def check_connection() -> tuple[bool, str]:
    if not settings.attachments_enabled():
        return False, "Dosya yükleme ayarları ([drive] upload_url, upload_token) eksik."
    try:
        result = _call("ping")
    except AttachmentError as exc:
        return False, str(exc)
    return True, f"Dosya servisi çalışıyor ({result.get('account', '')})."
