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
