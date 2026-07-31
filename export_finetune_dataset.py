#!/usr/bin/env python3
"""Ham logs/events.jsonl'i (asla degistirmeden) fine-tuning icin kullanilabilir
bir JSONL veri setine ({system, user, tools, output, label}) donusturur.

Idempotent: her calistirmada kaynak log'u okur, yeni bir cikti dosyasi uretir
(zaman damgali). Iki kaynak turunden kayit uretir:
  1. "llm_call" step'i (gercek LLM cagrisi) - tercihen "argument_binding"
     fazi (isimlendirilmis tool_choice ile enum-kisitli uretilen, gercek
     kanit tasiyan cagri); yoksa gruptaki son llm_call kullanilir.
  2. "invocation_decision" step'i, llm_invoked=False (skip_llm=True) - LLM'e
     hic gidilmeyen otomatik-cozulmus istekler; "cagrilsaydi boyle cevap
     vermeliydi" seklinde sentetik bir hedef uretir.
Varsa ayni request_id'ye ait "feedback" event'inden bir "label" eklenir
(correct/incorrect/unlabeled) - fine-tune oncesi hatali orneklerin
filtrelenmesini kolaylastirmak icin."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from aegis import config

DEFAULT_OUTPUT_DIR = config.PROJECT_ROOT / "data" / "finetune"


def load_events(path: Path) -> list[dict]:
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def _group_by_request(events: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        groups[event["request_id"]].append(event)
    return groups


def _pick_llm_call(group: list[dict]) -> dict | None:
    llm_calls = [e for e in group if e.get("step") == "llm_call"]
    if not llm_calls:
        return None
    for event in llm_calls:
        if (event.get("extra") or {}).get("phase") == "argument_binding":
            return event
    return llm_calls[-1]


def _pick_skip_llm_decision(group: list[dict]) -> dict | None:
    for event in group:
        if event.get("step") == "invocation_decision" and event.get("llm_invoked") is False:
            return event
    return None


def _find_label(group: list[dict]) -> str:
    for event in group:
        if event.get("step") == "feedback":
            feedback = event.get("user_feedback")
            if feedback == "dogru":
                return "correct"
            if feedback == "yanlis":
                return "incorrect"
    return "unlabeled"


def build_records(events: list[dict]) -> list[dict]:
    records = []
    for request_id, group in _group_by_request(events).items():
        label = _find_label(group)

        llm_event = _pick_llm_call(group)
        if llm_event is not None:
            records.append(
                {
                    "request_id": request_id,
                    "system": llm_event.get("system_prompt"),
                    "user": llm_event.get("raw_user_message"),
                    "tools": llm_event.get("tool_schemas_sent"),
                    "output": llm_event.get("raw_completion"),
                    "label": label,
                }
            )
            continue

        decision_event = _pick_skip_llm_decision(group)
        if decision_event is not None:
            auto_resolved = (decision_event.get("extra") or {}).get("auto_resolved")
            records.append(
                {
                    "request_id": request_id,
                    "system": None,
                    "user": decision_event.get("raw_user_message"),
                    "tools": None,
                    "output": {
                        "tool": decision_event.get("tool"),
                        "args": auto_resolved,
                        "synthetic": True,
                    },
                    "label": label,
                }
            )
    return records


def export(input_path: Path, output_dir: Path) -> Path:
    events = load_events(input_path)
    records = build_records(events)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"dataset_{timestamp}.jsonl"

    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=config.LOG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_path = export(args.input, args.output_dir)
    print(f"{output_path} yazildi.")


if __name__ == "__main__":
    main()
