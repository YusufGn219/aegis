import json

from aegis.logging_.event_log import LogEvent, StructuredLogger, Timer


def test_log_writes_one_json_line(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = StructuredLogger(path=str(log_path))
    logger.log(LogEvent(request_id="abc-123", step="extraction", decision="ok", success=True))

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["request_id"] == "abc-123"
    assert parsed["step"] == "extraction"
    assert parsed["success"] is True


def test_log_appends_multiple_lines(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = StructuredLogger(path=str(log_path))
    logger.log(LogEvent(request_id="r1", step="extraction"))
    logger.log(LogEvent(request_id="r1", step="llm_call"))

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_timer_measures_duration():
    with Timer() as t:
        pass
    assert t.duration_ms >= 0


def test_log_with_finetune_fields_serializes(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = StructuredLogger(path=str(log_path))
    logger.log(
        LogEvent(
            request_id="r1",
            step="llm_call",
            raw_user_message="rapor.pdf dosyasini tasi",
            system_prompt="Sen bir workspace asistanisin...",
            prompt_version="v2",
            tool_schemas_sent=[{"type": "function", "function": {"name": "move_file"}}],
            raw_completion='{"tool_calls": []}',
            session_id="s1",
            turn_index=0,
            user_feedback=None,
        )
    )

    parsed = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert parsed["prompt_version"] == "v2"
    assert parsed["session_id"] == "s1"
    assert parsed["turn_index"] == 0
    assert parsed["tool_schemas_sent"][0]["function"]["name"] == "move_file"


def test_log_without_finetune_fields_defaults_to_none(tmp_path):
    """Eski (55 satirlik) loglarla geriye donuk uyumluluk: yeni alanlar
    verilmezse None olarak serialize edilir, eski satirlar bozulmaz."""
    log_path = tmp_path / "events.jsonl"
    logger = StructuredLogger(path=str(log_path))
    logger.log(LogEvent(request_id="r1", step="extraction"))

    parsed = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert parsed["session_id"] is None
    assert parsed["raw_completion"] is None
