"""Yapisal, append-only JSONL log. Alan secimi bilerek ileride DuckDB'ye
yuklenebilir duz bir semada (orn. duckdb.sql("... read_json_auto(...)")) -
DuckDB entegrasyonunun kendisi bu fazda YAZILMIYOR, sadece format hazir."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from aegis import config


@dataclass
class LogEvent:
    request_id: str
    step: str  # "session_start" | "extraction" | "invocation_decision" | "llm_call" | "path_resolution" | "permission" | "tool_execute" | "feedback"
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str | None = None
    skill: str | None = None
    tool: str | None = None
    llm_invoked: bool = False
    tokens_prompt: int | None = None
    tokens_completion: int | None = None
    duration_ms: float | None = None
    decision: str = ""
    success: bool | None = None
    extra: dict | None = None
    # Fine-tuning veri toplama icin eklenen alanlar (hepsi opsiyonel - eski
    # loglarla geriye donuk uyumluluk bozulmaz). system_prompt/prompt_version/
    # tool_schemas_sent/raw_completion SADECE "llm_call" step'inde doldurulur;
    # diger step'lerde tekrari onlemek icin None birakilir.
    raw_user_message: str | None = None
    system_prompt: str | None = None
    prompt_version: str | None = None
    tool_schemas_sent: list[dict] | None = None
    raw_completion: str | None = None
    session_id: str | None = None
    turn_index: int | None = None
    user_feedback: str | None = None


class StructuredLogger:
    def __init__(self, path: str | None = None):
        self.path = path or str(config.LOG_PATH)

    def log(self, event: LogEvent) -> None:
        import os

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")


class Timer:
    """Kucuk yardimci: `with Timer() as t: ...` sonra t.duration_ms kullanilir."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.duration_ms = (time.perf_counter() - self._start) * 1000
