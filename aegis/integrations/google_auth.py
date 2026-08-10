"""Gmail + Calendar icin ORTAK Google OAuth akisi. Tum scope'lar tek bir
token.json'da birlikte tutulur (ayri ayri yetkilendirme akisi/dosyasi yok) -
bu yuzden yeni bir scope eklendiginde eski token.json gecersiz kalir ve
kullanicinin bir kez daha tarayicidan onay vermesi gerekir (bkz. README)."""

from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from aegis import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleAuthError(Exception):
    """credentials.json eksik/gecersiz ya da yetkilendirme tamamlanamadi."""


def load_credentials() -> Credentials:
    creds: Credentials | None = None
    if config.GOOGLE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        config.GOOGLE_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not config.GOOGLE_CREDENTIALS_PATH.exists():
        raise GoogleAuthError(
            f"'{config.GOOGLE_CREDENTIALS_PATH}' bulunamadi. Google Cloud Console'dan "
            "bir 'Desktop app' OAuth client'i olusturup credentials.json olarak "
            "buraya koyman gerekiyor (bkz. README - Google Kurulumu)."
        )

    # Ilk yetkilendirme (ya da scope degistiginde yeniden yetkilendirme):
    # tarayici acilir, kullanici onaylar.
    flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    config.GOOGLE_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds
