"""CalendarSkill artik gercek Google Calendar API'sine (aegis.integrations.
calendar_client) bagli oldugundan, buradaki testler o modulun fonksiyonlarini
mock'layip yukari akisi (extraction/resolution/permission/tool secimi)
dogrular - gercek ag cagrisi yapilmaz. Gercek canli-API dogrulamasi icin
elle test (bkz. proje notlari) veya ayri bir integration testi gerekir."""

from unittest.mock import patch

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.calendar_skill import CalendarSkill
from tests.unit.conftest import fake_tool_call_response


def test_add_event_via_llm_mocked_creates_calendar_event(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "add_event", '{"title": "Toplanti", "date": "15.08.2026"}'
        ),
    )

    with patch("aegis.tools.add_event_tool.add_event", return_value="evt-1") as mock_add:
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run("15.08.2026 tarihinde 'Toplanti' etkinligi ekle.", "req-event", logger)

    assert result.success is True
    mock_add.assert_called_once_with("Toplanti", "15.08.2026", None, None)
    assert result.data["event_id"] == "evt-1"


def test_add_event_declined_permission_does_not_call_api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "add_event", '{"title": "Toplanti", "date": "15.08.2026"}'
        ),
    )

    with patch("aegis.tools.add_event_tool.add_event") as mock_add:
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run(
            "15.08.2026 tarihinde 'Toplanti' etkinligi ekle.", "req-event-declined", logger
        )

    assert result.success is False
    mock_add.assert_not_called()


def test_list_events_via_llm_mocked_lists_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_events", "{}"),
    )

    with patch("aegis.tools.list_events_tool.list_all_events", return_value=[]):
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run("Etkinliklerimi listele.", "req-list-events", logger)

    assert result.success is True
    assert result.data == {"events": []}


def test_add_event_with_time_and_recurrence_via_llm_mocked(tmp_path, monkeypatch):
    # Iki tirnakli ifade KASITLI - title adaylari (quoted_spans) 2 elemanli
    # olunca invocation_policy skip_llm=False donuyor (tam 1 aday sarti
    # bozuluyor), akis LLM'e dusuyor.
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "add_event",
            '{"title": "Spor", "date": "15.08.2026", "time": "07:30", "recurrence": "haftalik"}',
        ),
    )

    with patch("aegis.tools.add_event_tool.add_event", return_value="evt-2") as mock_add:
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run(
            "15.08.2026 saat 07:30'da 'Spor' ya da 'Antrenman' etkinligini haftalik olarak ekle.",
            "req-event-recurring",
            logger,
        )

    assert result.success is True
    mock_add.assert_called_once_with("Spor", "15.08.2026", "07:30", "haftalik")


def test_add_event_with_time_and_recurrence_skips_llm_when_unambiguous(tmp_path, monkeypatch):
    # title/date TEK adaylik (tek tirnakli ifade, tek tarih) -> invocation_policy
    # skip_llm=True doner. LLM mock'u KASITLI cagrilmiyor (monkeypatch yok) -
    # eger kod yanlislikla LLM'e duserse test bir gercek HTTP cagrisi denemeye
    # calisip patlar. Bu, saat/tekrarin artik LLM'siz otomatik yolda da
    # dogru gectigini kanitlar (bkz. invocation_policy.decide() optional_slots).
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    with patch("aegis.tools.add_event_tool.add_event", return_value="evt-3") as mock_add:
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run(
            "15.08.2026 tarihinde saat 07:30 'Spor' etkinligini haftalik olarak ekle.",
            "req-event-recurring-skip-llm",
            logger,
        )

    assert result.success is True
    mock_add.assert_called_once_with("Spor", "15.08.2026", "07:30", "haftalik")


def test_list_upcoming_events_returns_client_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    fake_events = [
        {"title": "Bugun", "when": "2026-08-15", "recurring": False},
        {"title": "Gelecek", "when": "2026-08-20", "recurring": True},
    ]
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_upcoming_events", "{}"),
    )

    with patch("aegis.tools.list_upcoming_events_tool.list_upcoming_events", return_value=fake_events):
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run("Yaklasan etkinliklerimi hatirlat.", "req-upcoming", logger)

    assert result.success is True
    titles = [e["title"] for e in result.data["events"]]
    assert titles == ["Bugun", "Gelecek"]


def test_add_event_calendar_api_error_returns_failure(tmp_path, monkeypatch):
    from aegis.integrations.calendar_client import CalendarApiError

    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "add_event", '{"title": "Toplanti", "date": "15.08.2026"}'
        ),
    )

    with patch(
        "aegis.tools.add_event_tool.add_event",
        side_effect=CalendarApiError("Calendar API ekleme hatasi: 403"),
    ):
        skill = CalendarSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run("15.08.2026 tarihinde 'Toplanti' etkinligi ekle.", "req-event-error", logger)

    assert result.success is False
    assert "403" in result.message
