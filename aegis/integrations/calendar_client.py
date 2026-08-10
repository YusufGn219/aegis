"""Google Calendar API uzerinden GERCEK etkinlik olusturma/listeleme
(calendar.events scope - takvim ayarlarina/paylasima dokunmaz). OAuth akisi
google_auth'ta ORTAK (Gmail ile paylasilir).

Tarih/saat: candidates.py'nin dogrulama yapmadan aynen tuttugu ham metin
("GG.AA.YYYY" / "SS:DD") burada sabit bir saat dilimiyle RFC3339'a cevrilir.
Saat verilmemisse gun-boyu (all-day) etkinlik olusturulur. Tekrar (haftalik/
aylik) Google'in kendi RRULE mekanizmasina devredilir - "yaklasan etkinlikleri
listele" artik yerel bir tarih-filtreleme dongusune degil, dogrudan Calendar
API'nin timeMin/singleEvents/orderBy parametrelerine dayanir."""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aegis.integrations.google_auth import load_credentials

TIMEZONE = "Europe/Istanbul"
CALENDAR_ID = "primary"

RECURRENCE_RRULE = {
    "gunluk": "RRULE:FREQ=DAILY",
    "haftalik": "RRULE:FREQ=WEEKLY",
    "aylik": "RRULE:FREQ=MONTHLY",
}


class CalendarApiError(Exception):
    """Yetkilendirme basarili ama Calendar API istegi reddetti."""


class CalendarInputError(Exception):
    """Tarih/saat metni beklenen formatta degil - kullaniciya gosterilecek net mesaj."""


def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError as exc:
        raise CalendarInputError(
            f"Gecersiz tarih formati: '{date_str}' (beklenen: GG.AA.YYYY)"
        ) from exc


def _parse_time(time_str: str):
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError as exc:
        raise CalendarInputError(f"Gecersiz saat formati: '{time_str}' (beklenen: SS:DD)") from exc


def add_event(title: str, date: str, time: str | None, recurrence: str | None) -> str:
    """Google Calendar'a yeni bir etkinlik ekler, Google'in event id'sini doner."""
    creds = load_credentials()
    service = build("calendar", "v3", credentials=creds)

    event_date = _parse_date(date)
    body: dict = {"summary": title}

    if time:
        event_time = _parse_time(time)
        start_dt = datetime.combine(event_date, event_time, tzinfo=ZoneInfo(TIMEZONE))
        end_dt = start_dt + timedelta(hours=1)
        body["start"] = {"dateTime": start_dt.isoformat()}
        body["end"] = {"dateTime": end_dt.isoformat()}
    else:
        body["start"] = {"date": event_date.isoformat()}
        body["end"] = {"date": (event_date + timedelta(days=1)).isoformat()}

    rrule = RECURRENCE_RRULE.get(recurrence) if recurrence else None
    if rrule:
        body["recurrence"] = [rrule]

    try:
        created = service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Calendar API ekleme hatasi: {exc}") from exc

    return created["id"]


def _describe_event(event: dict) -> dict:
    start = event.get("start", {})
    return {
        "title": event.get("summary", "(basliksiz)"),
        "when": start.get("dateTime") or start.get("date", ""),
        "recurring": bool(event.get("recurringEventId") or event.get("recurrence")),
    }


def _list_events(time_min: datetime, time_max: datetime | None, max_results: int) -> list[dict]:
    creds = load_credentials()
    service = build("calendar", "v3", credentials=creds)

    params = {
        "calendarId": CALENDAR_ID,
        "timeMin": time_min.isoformat(),
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max is not None:
        params["timeMax"] = time_max.isoformat()

    try:
        result = service.events().list(**params).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Calendar API listeleme hatasi: {exc}") from exc

    return [_describe_event(e) for e in result.get("items", [])]


def list_upcoming_events(max_results: int = 10) -> list[dict]:
    """Su andan itibaren yaklasan etkinlikleri doner."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    return _list_events(time_min=now, time_max=None, max_results=max_results)


def list_all_events(max_results: int = 20) -> list[dict]:
    """Son 90 gun ile gelecek 365 gun arasindaki etkinlikleri doner - "tum
    zamanlar" sinirsiz sorgulanmadi (sonsuz tekrarli etkinliklerde pahali/
    anlamsiz olurdu), makul bir pencereyle sinirlandirildi."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    return _list_events(
        time_min=now - timedelta(days=90),
        time_max=now + timedelta(days=365),
        max_results=max_results,
    )


def find_events_by_title(title: str, max_results: int = 10) -> list[dict]:
    """Baslikla (Google'in tam-metin arama parametresi `q` ile) eslesen
    etkinlikleri doner - delete_event_tool'un kullaniciya "hangi etkinlik"
    demeden ONCE gercek adaylari gormesi icin. Gecmis 365 - gelecek 365 gun
    penceresiyle sinirli (silme genelde yakin zamanli bir etkinligi hedefler)."""
    creds = load_credentials()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(ZoneInfo(TIMEZONE))

    try:
        result = (
            service.events()
            .list(
                calendarId=CALENDAR_ID,
                q=title,
                timeMin=(now - timedelta(days=365)).isoformat(),
                timeMax=(now + timedelta(days=365)).isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except HttpError as exc:
        raise CalendarApiError(f"Calendar API arama hatasi: {exc}") from exc

    return [{"id": e["id"], **_describe_event(e)} for e in result.get("items", [])]


def update_event(
    event_id: str, date: str | None, time: str | None, recurrence: str | None
) -> dict:
    """Var olan bir etkinligin tarih/saat/tekrarini gunceller (baslik/diger
    alanlar dokunulmadan kalir - Calendar API'nin patch'i sadece body'de
    verilen ust-seviye alanlari degistirir). date/time'dan sadece biri
    verilirse digeri MEVCUT etkinlikten alinir (orn. sadece saat degisirse
    tarih aynı kalir) - kullanicinin belirtmedigi bir seyi sessizce
    degistirmemek icin."""
    creds = load_credentials()
    service = build("calendar", "v3", credentials=creds)

    try:
        existing = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Calendar API okuma hatasi: {exc}") from exc

    body: dict = {}

    if date or time:
        existing_start = existing.get("start", {})
        is_all_day = "date" in existing_start and "dateTime" not in existing_start

        if date:
            event_date = _parse_date(date)
        elif is_all_day:
            event_date = date_cls.fromisoformat(existing_start["date"])
        else:
            event_date = datetime.fromisoformat(existing_start["dateTime"]).date()

        if time:
            event_time = _parse_time(time)
            start_dt = datetime.combine(event_date, event_time, tzinfo=ZoneInfo(TIMEZONE))
            end_dt = start_dt + timedelta(hours=1)
            body["start"] = {"dateTime": start_dt.isoformat()}
            body["end"] = {"dateTime": end_dt.isoformat()}
        elif not is_all_day:
            # Sadece tarih degisiyor, mevcut saat-of-day ve sureyi koru.
            existing_start_dt = datetime.fromisoformat(existing_start["dateTime"])
            existing_end_dt = datetime.fromisoformat(existing["end"]["dateTime"])
            duration = existing_end_dt - existing_start_dt
            start_dt = existing_start_dt.replace(
                year=event_date.year, month=event_date.month, day=event_date.day
            )
            body["start"] = {"dateTime": start_dt.isoformat()}
            body["end"] = {"dateTime": (start_dt + duration).isoformat()}
        else:
            body["start"] = {"date": event_date.isoformat()}
            body["end"] = {"date": (event_date + timedelta(days=1)).isoformat()}

    if recurrence:
        rrule = RECURRENCE_RRULE.get(recurrence)
        if rrule:
            body["recurrence"] = [rrule]

    try:
        updated = service.events().patch(calendarId=CALENDAR_ID, eventId=event_id, body=body).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Calendar API guncelleme hatasi: {exc}") from exc

    return _describe_event(updated)


def delete_event(event_id: str) -> None:
    creds = load_credentials()
    service = build("calendar", "v3", credentials=creds)
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except HttpError as exc:
        raise CalendarApiError(f"Calendar API silme hatasi: {exc}") from exc
