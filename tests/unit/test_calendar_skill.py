import json
import os

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.calendar_skill import CalendarSkill
from tests.unit.conftest import fake_tool_call_response


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
    assert events == [{"title": "Toplanti", "date": "15.08.2026"}]


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
