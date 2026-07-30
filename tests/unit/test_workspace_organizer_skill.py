"""Bu testler LLM'e HIC gitmeyen (skip_llm) yolu kapsar - ag/sunucu gerekmez.
LLM'e gerceten giden yol (belirsizlik durumu) icin bkz.
tests/integration/test_workspace_organizer_skill_integration.py"""

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.workspace_organizer_skill import WorkspaceOrganizerSkill


def _make_sandbox(tmp_path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "rapor.pdf").write_text("dummy")
    (tmp_path / "Arsiv").mkdir()
    return tmp_path


def test_skip_llm_path_moves_file_without_calling_llm(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    def fail_if_llm_called(_request):
        raise AssertionError("Bu senaryoda LLM'e hic gidilmemeliydi (skip_llm=True bekleniyordu)")

    monkeypatch.setattr(
        "aegis.skills.workspace_organizer_skill.llm_client.call_for_tool_selection",
        fail_if_llm_called,
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini Arsiv klasorune tasi.", "req-1", logger)

    assert result.success is True
    assert not (sandbox / "Downloads" / "rapor.pdf").exists()
    assert (sandbox / "Arsiv" / "rapor.pdf").exists()


def test_skip_llm_path_declined_permission_does_not_move_file(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    def fail_if_llm_called(_request):
        raise AssertionError("Bu senaryoda LLM'e hic gidilmemeliydi")

    monkeypatch.setattr(
        "aegis.skills.workspace_organizer_skill.llm_client.call_for_tool_selection",
        fail_if_llm_called,
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini Arsiv klasorune tasi.", "req-2", logger)

    assert result.success is False
    assert (sandbox / "Downloads" / "rapor.pdf").exists()


def test_no_relevant_candidates_still_reaches_llm_and_llm_is_mocked(tmp_path, monkeypatch):
    """Hicbir tool'a dair kanit olmayan bir mesaj (orn. hava durumu) icin de
    LLM'e gidilir (mock'lanmis bir 'refuse' cevabi donduruyoruz)."""
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)

    class _FakeMessage:
        tool_calls = None
        content = "Uzgunum, bu konuda yardimci olamam."

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeUsage:
        prompt_tokens = 10
        completion_tokens = 5

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = _FakeUsage()

    monkeypatch.setattr(
        "aegis.skills.workspace_organizer_skill.llm_client.call_for_tool_selection",
        lambda _request: _FakeResponse(),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("Bugun hava nasil?", "req-3", logger)

    assert result.success is False
    assert "yardimci olamam" in result.message
