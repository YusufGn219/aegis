import json
import os
from datetime import date as date_cls

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.calendar_skill import CalendarSkill
from tests.unit.conftest import fake_tool_call_response


class _FixedToday(date_cls):
    """date.today() 15.08.2026'yi dondurecek sekilde sabitlenir (list_upcoming_
    events testlerinde deterministik 'bugun' icin)."""

    @classmethod
    def today(cls):
        return date_cls(2026, 8, 15)


def test_add_event_via_llm_mocked_writes_calendar_json(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "add_event", '{"title": "Toplanti", "date": "15.08.2026"}'
        ),
    )

    skill = CalendarSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("15.08.2026 tarihinde 'Toplanti' etkinligi ekle.", "req-event", logger)

    assert result.success is True
    calendar_path = os.path.join(str(tmp_path), "calendar.json")
    events = json.loads(open(calendar_path, encoding="utf-8").read())
    assert events == [
        {"title": "Toplanti", "date": "15.08.2026", "time": None, "recurrence": None}
    ]


def test_add_event_declined_permission_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "add_event", '{"title": "Toplanti", "date": "15.08.2026"}'
        ),
    )

    skill = CalendarSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("15.08.2026 tarihinde 'Toplanti' etkinligi ekle.", "req-event-declined", logger)

    assert result.success is False
    assert not os.path.exists(os.path.join(str(tmp_path), "calendar.json"))


def test_list_events_via_llm_mocked_lists_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_events", "{}"),
    )

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

    skill = CalendarSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run(
        "15.08.2026 saat 07:30'da 'Spor' ya da 'Antrenman' etkinligini haftalik olarak ekle.",
        "req-event-recurring",
        logger,
    )

    assert result.success is True
    calendar_path = os.path.join(str(tmp_path), "calendar.json")
    events = json.loads(open(calendar_path, encoding="utf-8").read())
    assert events == [
        {"title": "Spor", "date": "15.08.2026", "time": "07:30", "recurrence": "haftalik"}
    ]


def test_add_event_with_time_and_recurrence_skips_llm_when_unambiguous(tmp_path, monkeypatch):
    # title/date TEK adaylik (tek tirnakli ifade, tek tarih) -> invocation_policy
    # skip_llm=True doner. LLM mock'u KASITLI cagrilmiyor (monkeypatch yok) -
    # eger kod yanlislikla LLM'e duserse test bir gercek HTTP cagrisi denemeye
    # calisip patlar. Bu, saat/tekrarin artik LLM'siz otomatik yolda da
    # dogru yazildigini kanitlar (bkz. invocation_policy.decide() optional_slots).
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    skill = CalendarSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run(
        "15.08.2026 tarihinde saat 07:30 'Spor' etkinligini haftalik olarak ekle.",
        "req-event-recurring-skip-llm",
        logger,
    )

    assert result.success is True
    calendar_path = os.path.join(str(tmp_path), "calendar.json")
    events = json.loads(open(calendar_path, encoding="utf-8").read())
    assert events == [
        {"title": "Spor", "date": "15.08.2026", "time": "07:30", "recurrence": "haftalik"}
    ]


def test_list_upcoming_events_filters_past_events(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("aegis.tools.list_upcoming_events_tool.date", _FixedToday)

    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text(
        json.dumps(
            [
                {"title": "Gecmis", "date": "01.01.2026", "time": None, "recurrence": None},
                {"title": "Bugun", "date": "15.08.2026", "time": None, "recurrence": None},
                {"title": "Gelecek", "date": "20.08.2026", "time": None, "recurrence": "aylik"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_upcoming_events", "{}"),
    )

    skill = CalendarSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("Yaklasan etkinliklerimi hatirlat.", "req-upcoming", logger)

    assert result.success is True
    titles = [e["title"] for e in result.data["events"]]
    assert titles == ["Bugun", "Gelecek"]
