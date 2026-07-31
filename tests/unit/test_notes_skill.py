import os

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.notes_skill import NotesSkill
from tests.unit.conftest import fake_tool_call_response


def test_create_note_via_llm_mocked_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "create_note", '{"title": "Alisveris listesi", "content": "sut, ekmek"}'
        ),
    )

    skill = NotesSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run(
        "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
        "req-note",
        logger,
    )

    assert result.success is True
    note_path = os.path.join(str(tmp_path), "Notlar", "Alisveris_listesi.txt")
    assert os.path.isfile(note_path)
    assert "sut, ekmek" in open(note_path, encoding="utf-8").read()


def test_create_note_declined_permission_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "create_note", '{"title": "Alisveris listesi", "content": "sut, ekmek"}'
        ),
    )

    skill = NotesSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run(
        "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
        "req-note-declined",
        logger,
    )

    assert result.success is False
    assert not os.path.isdir(os.path.join(str(tmp_path), "Notlar"))


def test_list_notes_via_llm_mocked_lists_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("list_notes", "{}"),
    )

    skill = NotesSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("Notlarimi listele.", "req-list-notes", logger)

    assert result.success is True
    assert result.data == {"notes": []}
