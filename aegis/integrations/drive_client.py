"""Google Drive API uzerinden GERCEK not olusturma/listeleme (drive.file
scope - SADECE bu uygulamanin kendi olusturdugu dosyalara erisir, kullanicinin
var olan Drive icerigine dokunmaz/goremez). OAuth akisi google_auth'ta ORTAK
(Gmail/Calendar ile paylasilir).

Google Keep API kisisel (@gmail.com) hesaplarda KULLANILAMIYOR - sadece
Workspace admin'in actigi kurumsal hesaplarda calisiyor, bu yuzden notlar
Drive'da duz metin dosyasi olarak tutuluyor. Hepsi tek bir "aegis Notlar"
klasorunde - local sandbox'taki "Notlar/" klasorunun canli karsiligi."""

from __future__ import annotations

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaInMemoryUpload

from aegis.integrations.google_auth import load_credentials

NOTES_FOLDER_NAME = "aegis Notlar"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
TEXT_MIME_TYPE = "text/plain"


class DriveApiError(Exception):
    """Yetkilendirme basarili ama Drive API istegi reddetti."""


def _get_service():
    creds = load_credentials()
    return build("drive", "v3", credentials=creds)


def _find_notes_folder_id(service) -> str | None:
    query = (
        f"name = '{NOTES_FOLDER_NAME}' and mimeType = '{FOLDER_MIME_TYPE}' "
        "and trashed = false"
    )
    result = service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None


def _get_or_create_notes_folder_id(service) -> str:
    folder_id = _find_notes_folder_id(service)
    if folder_id:
        return folder_id
    created = (
        service.files()
        .create(body={"name": NOTES_FOLDER_NAME, "mimeType": FOLDER_MIME_TYPE}, fields="id")
        .execute()
    )
    return created["id"]


def _find_note_by_title(service, folder_id: str, title: str) -> dict | None:
    escaped_title = title.replace("'", "\\'")
    query = f"name = '{escaped_title}' and '{folder_id}' in parents and trashed = false"
    result = service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    files = result.get("files", [])
    return files[0] if files else None


def create_note(title: str, content: str) -> str:
    """Drive'da "aegis Notlar" klasorunde yeni bir metin dosyasi olusturur.
    Ayni baslikla zaten bir not varsa (local davranisla ayni) OLUSTURMAZ,
    DriveApiError firlatir - ustune yazma yok."""
    try:
        service = _get_service()
        folder_id = _get_or_create_notes_folder_id(service)

        if _find_note_by_title(service, folder_id, title):
            raise DriveApiError(f"Not zaten var: '{title}'")

        media = MediaInMemoryUpload(
            f"{title}\n\n{content}\n".encode("utf-8"), mimetype=TEXT_MIME_TYPE
        )
        created = (
            service.files()
            .create(
                body={"name": title, "mimeType": TEXT_MIME_TYPE, "parents": [folder_id]},
                media_body=media,
                fields="id",
            )
            .execute()
        )
    except HttpError as exc:
        raise DriveApiError(f"Drive API olusturma hatasi: {exc}") from exc

    return created["id"]


def find_notes_by_title(title: str, max_results: int = 10) -> list[dict]:
    """delete_note_tool/update_note_tool'un kullaniciya "hangi not" demeden
    ONCE gercek adaylari gormesi icin. create_note ayni baslikla ikinci bir
    dosya olusturmayi zaten reddettigi icin normalde tek eslesme cikar, ama
    Drive'a elle/baska yoldan eklenmis ayni isimli dosyalar da olabilir -
    bu yuzden delete_event_tool'daki gibi 0/1/2+ ayrimi yapiliyor."""
    service = _get_service()
    folder_id = _find_notes_folder_id(service)
    if folder_id is None:
        return []

    escaped_title = title.replace("'", "\\'")
    query = f"name = '{escaped_title}' and '{folder_id}' in parents and trashed = false"
    try:
        result = (
            service.files()
            .list(q=query, fields="files(id, name, modifiedTime)", pageSize=max_results)
            .execute()
        )
    except HttpError as exc:
        raise DriveApiError(f"Drive API arama hatasi: {exc}") from exc

    return [
        {"id": f["id"], "title": f["name"], "modified": f.get("modifiedTime", "")}
        for f in result.get("files", [])
    ]


def update_note(file_id: str, content: str) -> dict:
    """Var olan bir notun icerigini TAMAMEN yeni `content` ile degistirir
    (baslik/dosya adi ayni kalir - yeniden adlandirma desteklenmiyor, bkz.
    update_note_tool docstring'i)."""
    service = _get_service()
    try:
        existing = service.files().get(fileId=file_id, fields="name").execute()
        media = MediaInMemoryUpload(
            f"{existing['name']}\n\n{content}\n".encode("utf-8"), mimetype=TEXT_MIME_TYPE
        )
        updated = (
            service.files()
            .update(fileId=file_id, media_body=media, fields="name, modifiedTime")
            .execute()
        )
    except HttpError as exc:
        raise DriveApiError(f"Drive API guncelleme hatasi: {exc}") from exc

    return {"title": updated["name"], "modified": updated.get("modifiedTime", "")}


def delete_note(file_id: str) -> None:
    service = _get_service()
    try:
        service.files().delete(fileId=file_id).execute()
    except HttpError as exc:
        raise DriveApiError(f"Drive API silme hatasi: {exc}") from exc


def list_notes() -> list[dict]:
    """"aegis Notlar" klasorundeki notlari (isim/degistirilme tarihi)
    doner, en son degistirilen once."""
    try:
        service = _get_service()
        folder_id = _find_notes_folder_id(service)
        if folder_id is None:
            return []

        result = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(name, modifiedTime)",
                orderBy="modifiedTime desc",
                pageSize=50,
            )
            .execute()
        )
    except HttpError as exc:
        raise DriveApiError(f"Drive API listeleme hatasi: {exc}") from exc

    return [{"title": f["name"], "modified": f["modifiedTime"]} for f in result.get("files", [])]
