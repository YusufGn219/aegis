"""Gmail API uzerinden GERCEK e-posta gonderimi ve okuma (gmail.send +
gmail.readonly scope - silme/etiket degistirme yetkisi yok). credentials.json
Google Cloud Console'dan
indirilen bir "Desktop app" OAuth client'idir; ilk cagrida tarayici acilip
kullanicidan onay istenir, sonrasi token.json'dan sessizce yenilenir.

Bu modul kasitli olarak aegis.tools.send_email_tool'dan ayri: tool katmani
sadece "ne gonderilecek"le ilgilenir, bu modul "nasil gonderilecek"le.
"""

from __future__ import annotations

import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aegis import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailAuthError(Exception):
    """credentials.json eksik/gecersiz ya da yetkilendirme tamamlanamadi."""


class GmailApiError(Exception):
    """Yetkilendirme basarili ama Gmail API istegi (gonderim/okuma) reddetti."""


def _load_credentials() -> Credentials:
    creds: Credentials | None = None
    if config.GMAIL_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(config.GMAIL_TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        config.GMAIL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not config.GMAIL_CREDENTIALS_PATH.exists():
        raise GmailAuthError(
            f"'{config.GMAIL_CREDENTIALS_PATH}' bulunamadi. Google Cloud Console'dan "
            "bir 'Desktop app' OAuth client'i olusturup credentials.json olarak "
            "buraya koyman gerekiyor (bkz. README - Gmail Kurulumu)."
        )

    # Ilk yetkilendirme: tarayici acilir, kullanici onaylar.
    flow = InstalledAppFlow.from_client_secrets_file(str(config.GMAIL_CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    config.GMAIL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def send_email(to: str, subject: str, body: str) -> str:
    """Gmail API ile gercek e-posta gonderir. Basarili olursa Gmail'in
    atadigi mesaj id'sini doner. Yetkilendirme veya API hatasinda
    GmailAuthError/GmailApiError firlatir - cagiran (send_email_tool)
    bunlari yakalayip ToolResult(success=False, ...) haline getirir."""
    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except HttpError as exc:
        raise GmailApiError(f"Gmail API gonderim hatasi: {exc}") from exc

    return sent["id"]


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def list_recent_emails(max_results: int = 5) -> list[dict]:
    """Gelen kutusundaki en son `max_results` mesajin ozetini doner
    (from/subject/date/snippet). gmail.readonly scope'u yeter - govde
    tam olarak cekilmez, sadece metadata + Gmail'in kendi snippet'i."""
    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds)

    try:
        listing = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
            .execute()
        )
        message_refs = listing.get("messages", [])

        emails = []
        for ref in message_refs:
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            emails.append(
                {
                    "from": _header(headers, "From"),
                    "subject": _header(headers, "Subject"),
                    "date": _header(headers, "Date"),
                    "snippet": msg.get("snippet", ""),
                }
            )
    except HttpError as exc:
        raise GmailApiError(f"Gmail API okuma hatasi: {exc}") from exc

    return emails
