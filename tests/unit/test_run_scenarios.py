import pytest

from run_scenarios import SCENARIOS, _actual_tool, _fake_input_queue, _seed


def test_fake_input_queue_returns_answers_in_order():
    fake_input = _fake_input_queue(["y", "n"])
    assert fake_input("prompt1") == "y"
    assert fake_input("prompt2") == "n"


def test_fake_input_queue_raises_when_exhausted():
    fake_input = _fake_input_queue([])
    with pytest.raises(AssertionError):
        fake_input("prompt")


def test_seed_creates_expected_folders_and_files(tmp_path):
    _seed(tmp_path)
    assert (tmp_path / "Downloads" / "rapor.pdf").is_file()
    assert (tmp_path / "Arşiv").is_dir()
    assert (tmp_path / "Belgeler").is_dir()
    # Yedek/Yedek2026 kasitli olarak seed edilmiyor (create_folder basari
    # senaryolari icin bos olmalari gerekiyor).
    assert not (tmp_path / "Yedek").exists()


def test_seed_is_idempotent(tmp_path):
    _seed(tmp_path)
    (tmp_path / "Downloads" / "extra.txt").write_text("x", encoding="utf-8")
    _seed(tmp_path)
    assert not (tmp_path / "Downloads" / "extra.txt").exists()


def test_actual_tool_picks_last_non_null_tool_field():
    events = [
        {"request_id": "r1", "step": "extraction", "tool": None},
        {"request_id": "r1", "step": "invocation_decision", "tool": "move_file"},
        {"request_id": "r1", "step": "tool_execute", "tool": "move_file"},
        {"request_id": "r2", "step": "tool_execute", "tool": "delete_file"},
    ]
    assert _actual_tool(events, "r1") == "move_file"


def test_actual_tool_returns_none_when_no_tool_called():
    events = [
        {"request_id": "r1", "step": "llm_call", "tool": None},
    ]
    assert _actual_tool(events, "r1") is None


def test_scenarios_are_well_formed_and_unique():
    prompts = [s[0] for s in SCENARIOS]
    assert len(prompts) == len(set(prompts)), "Tekrarlanan senaryo prompt'u var"
    for prompt, expected_tool, permission_answers, expected_success in SCENARIOS:
        assert isinstance(prompt, str) and prompt.strip()
        assert expected_tool is None or isinstance(expected_tool, str)
        assert isinstance(permission_answers, list)
        assert all(a in ("y", "n") for a in permission_answers)
        assert isinstance(expected_success, bool)
