"""Bu testler cogunlukla LLM'e HIC gitmeyen (skip_llm) yolu kapsar - ag/
sunucu gerekmez. copy_file eklendikten sonra move_file artik "filenames +
folder_names" slot seklini tek basina tasimiyor (copy_file de ayni sekli
paylasiyor) - bu yuzden "tasi"/"kopyala" gibi FIIL gerektiren senaryolar
artik LLM'e dusuyor (extraction sadece isim/nesneleri yakalar, fiilleri
degil). Bu testler o durumlarda LLM'i mock'layarak asagi akisi (resolution/
permission/execute) dogruluyor. Gercek canli-model dogrulamasi icin bkz.
tests/integration/test_vllm_tool_calls.py."""

import aegis.config as config
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.workspace_organizer_skill import WorkspaceOrganizerSkill
from tests.unit.conftest import fake_tool_call_response


def _make_sandbox(tmp_path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "rapor.pdf").write_text("dummy")
    (tmp_path / "Arsiv").mkdir()
    return tmp_path


def test_move_file_via_llm_mocked_moves_file(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "move_file", '{"source": "rapor.pdf", "destination": "Arsiv"}'
        ),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini Arsiv klasorune tasi.", "req-1", logger)

    assert result.success is True
    assert not (sandbox / "Downloads" / "rapor.pdf").exists()
    assert (sandbox / "Arsiv" / "rapor.pdf").exists()


def test_move_file_via_llm_mocked_declined_permission_does_not_move(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "move_file", '{"source": "rapor.pdf", "destination": "Arsiv"}'
        ),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini Arsiv klasorune tasi.", "req-2", logger)

    assert result.success is False
    assert (sandbox / "Downloads" / "rapor.pdf").exists()


def test_copy_file_via_llm_mocked_copies_file_leaving_source(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response(
            "copy_file", '{"source": "rapor.pdf", "destination": "Arsiv"}'
        ),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini Arsiv klasorune kopyala.", "req-copy", logger)

    assert result.success is True
    assert (sandbox / "Downloads" / "rapor.pdf").exists()
    assert (sandbox / "Arsiv" / "rapor.pdf").exists()


def test_delete_file_skip_llm_removes_file(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    def fail_if_llm_called(_request):
        raise AssertionError("Bu senaryoda LLM'e hic gidilmemeliydi (skip_llm=True bekleniyordu)")

    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        fail_if_llm_called,
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini sil.", "req-delete", logger)

    assert result.success is True
    assert not (sandbox / "Downloads" / "rapor.pdf").exists()


def test_delete_file_skip_llm_declined_permission_does_not_delete(tmp_path, monkeypatch):
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: (_ for _ in ()).throw(
            AssertionError("Bu senaryoda LLM'e hic gidilmemeliydi")
        ),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("rapor.pdf dosyasini sil.", "req-delete-declined", logger)

    assert result.success is False
    assert (sandbox / "Downloads" / "rapor.pdf").exists()


def test_create_folder_via_llm_mocked_creates_folder(tmp_path, monkeypatch):
    """create_folder, folder_names havuzunu list_files ile paylastigi icin
    (ikisi de tek slotlu) extraction seviyesinde asla tek basina
    kanitlanmis olamiyor - move_file/copy_file'in fiil (tasi/kopyala)
    belirsizligine benzer sekilde her zaman LLM'e dusuyor. Bu yuzden burada
    LLM mock'lanarak create_folder'i secen bir cevap simule ediliyor;
    gercek canli-model dogrulamasi icin bkz.
    tests/integration/test_vllm_tool_calls.py."""
    sandbox = _make_sandbox(tmp_path)
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: fake_tool_call_response("create_folder", '{"folder_name": "Yedek"}'),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("Yedek klasoru olustur.", "req-create-folder", logger)

    assert result.success is True
    assert (sandbox / "Yedek").is_dir()


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
        "aegis.skills.tool_selection_engine.llm_client.call_for_tool_selection",
        lambda _request: _FakeResponse(),
    )

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run("Bugun hava nasil?", "req-3", logger)

    assert result.success is False
    assert "yardimci olamam" in result.message
