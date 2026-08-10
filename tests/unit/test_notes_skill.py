"""NotesSkill artik gercek Google Drive API'sine (aegis.integrations.
drive_client) bagli oldugundan, buradaki testler o modulun fonksiyonlarini
mock'layip yukari akisi (extraction/permission/tool secimi) dogrular -
gercek ag cagrisi yapilmaz."""

from unittest.mock import patch

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.notes_skill import NotesSkill
from tests.unit.conftest import fake_tool_call_response


def test_create_note_via_llm_mocked_creates_drive_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "create_note", '{"title": "Alisveris listesi", "content": "sut, ekmek"}'
        ),
    )

    with patch("aegis.tools.create_note_tool.create_note", return_value="file-1") as mock_create:
        skill = NotesSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run(
            "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
            "req-note",
            logger,
        )

    assert result.success is True
    mock_create.assert_called_once_with("Alisveris listesi", "sut, ekmek")
    assert result.data["file_id"] == "file-1"


def test_create_note_declined_permission_does_not_call_api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "create_note", '{"title": "Alisveris listesi", "content": "sut, ekmek"}'
        ),
    )

    with patch("aegis.tools.create_note_tool.create_note") as mock_create:
        skill = NotesSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run(
            "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
            "req-note-declined",
            logger,
        )

    assert result.success is False
    mock_create.assert_not_called()


def test_create_note_duplicate_title_returns_failure(tmp_path, monkeypatch):
    from aegis.integrations.drive_client import DriveApiError

    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "create_note", '{"title": "Alisveris listesi", "content": "sut, ekmek"}'
        ),
    )

    with patch(
        "aegis.tools.create_note_tool.create_note",
        side_effect=DriveApiError("Not zaten var: 'Alisveris listesi'"),
    ):
        skill = NotesSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run(
            "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
            "req-note-dup",
            logger,
        )

    assert result.success is False
    assert "zaten var" in result.message


def test_list_notes_via_llm_mocked_lists_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_notes", "{}"),
    )

    with patch("aegis.tools.list_notes_tool.list_notes", return_value=[]):
        skill = NotesSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run("Notlarimi listele.", "req-list-notes", logger)

    assert result.success is True
    assert result.data == {"notes": []}


def test_list_notes_returns_client_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    fake_notes = [{"title": "Alisveris listesi", "modified": "2026-08-10T12:00:00Z"}]
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_notes", "{}"),
    )

    with patch("aegis.tools.list_notes_tool.list_notes", return_value=fake_notes):
        skill = NotesSkill()
        logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
        result = skill.run("Notlarimi listele.", "req-list-notes-data", logger)

    assert result.success is True
    assert result.data["notes"] == fake_notes
