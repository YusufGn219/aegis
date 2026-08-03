import json

from export_finetune_dataset import build_records, export, load_events


def _write_events(path, events):
    with open(path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def test_build_records_from_llm_call_prefers_argument_binding_phase():
    events = [
        {
            "request_id": "r1",
            "step": "llm_call",
            "extra": {"phase": "tool_selection", "raw_args": {"source": "dosya.txt"}},
            "raw_user_message": "bir dosyayi tasi",
            "system_prompt": "sys-v2",
            "tool_schemas_sent": [{"type": "function"}],
            "raw_completion": '{"tool_calls":[{"function":{"name":"move_file"}}]}',
        },
        {
            "request_id": "r1",
            "step": "llm_call",
            "extra": {"phase": "argument_binding", "raw_args": {"source": "YOK"}},
            "raw_user_message": "bir dosyayi tasi",
            "system_prompt": "sys-v2",
            "tool_schemas_sent": [{"type": "function", "function": {"name": "move_file"}}],
            "raw_completion": '{"tool_calls":[{"function":{"arguments":"{\\"source\\":\\"YOK\\"}"}}]}',
        },
    ]

    records = build_records(events)

    assert len(records) == 1
    assert records[0]["request_id"] == "r1"
    assert "YOK" in records[0]["output"]
    assert records[0]["label"] == "unlabeled"


def test_build_records_from_skip_llm_negative_example():
    events = [
        {
            "request_id": "r2",
            "step": "invocation_decision",
            "llm_invoked": False,
            "tool": "move_file",
            "raw_user_message": "rapor.pdf dosyasini Arsiv klasorune tasi",
            "extra": {"auto_resolved": {"source": "rapor.pdf", "destination": "Arsiv"}},
        },
    ]

    records = build_records(events)

    assert len(records) == 1
    assert records[0]["output"]["tool"] == "move_file"
    assert records[0]["output"]["args"] == {"source": "rapor.pdf", "destination": "Arsiv"}
    assert records[0]["output"]["synthetic"] is True


def test_build_records_applies_feedback_label():
    events = [
        {
            "request_id": "r3",
            "step": "invocation_decision",
            "llm_invoked": False,
            "tool": "list_files",
            "raw_user_message": "Arsiv klasorunu listele",
            "extra": {"auto_resolved": {"folder": "Arsiv"}},
        },
        {"request_id": "r3", "step": "feedback", "user_feedback": "yanlis"},
    ]

    records = build_records(events)

    assert records[0]["label"] == "incorrect"


def test_export_writes_jsonl_file(tmp_path):
    input_path = tmp_path / "events.jsonl"
    _write_events(
        input_path,
        [
            {
                "request_id": "r1",
                "step": "invocation_decision",
                "llm_invoked": False,
                "tool": "list_files",
                "raw_user_message": "Arsiv klasorunu listele",
                "extra": {"auto_resolved": {"folder": "Arsiv"}},
            }
        ],
    )

    output_dir = tmp_path / "out"
    output_path = export(input_path, output_dir)

    assert output_path.exists()
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["output"]["tool"] == "list_files"


def test_build_records_redacts_email_addresses():
    events = [
        {
            "request_id": "r4",
            "step": "invocation_decision",
            "llm_invoked": False,
            "tool": "send_email",
            "raw_user_message": "ahmet@sirket.com adresine mail at",
            "extra": {"auto_resolved": {"to": "ahmet@sirket.com"}},
        },
    ]

    records = build_records(events)

    assert "ahmet@sirket.com" not in records[0]["user"]
    assert records[0]["user"] == "[EMAIL_1] adresine mail at"
    assert records[0]["output"]["args"]["to"] == "[EMAIL_1]"


def test_build_records_redacts_filenames_and_folder_names_from_extraction_event():
    events = [
        {
            "request_id": "r5",
            "step": "extraction",
            "extra": {
                "candidates": {
                    "emails": [],
                    "filenames": ["rapor.pdf"],
                    "folder_names": ["Arsiv"],
                }
            },
        },
        {
            "request_id": "r5",
            "step": "invocation_decision",
            "llm_invoked": False,
            "tool": "move_file",
            "raw_user_message": "rapor.pdf dosyasini Arsiv klasorune tasi",
            "extra": {"auto_resolved": {"source": "rapor.pdf", "destination": "Arsiv"}},
        },
    ]

    records = build_records(events)

    assert records[0]["user"] == "[FILENAME_1] dosyasini [FOLDER_1] klasorune tasi"
    assert records[0]["output"]["args"] == {"source": "[FILENAME_1]", "destination": "[FOLDER_1]"}


def test_build_records_without_extraction_event_falls_back_to_email_regex_only():
    events = [
        {
            "request_id": "r6",
            "step": "invocation_decision",
            "llm_invoked": False,
            "tool": "send_email",
            "raw_user_message": "ahmet@sirket.com adresine mail at",
            "extra": {"auto_resolved": {"to": "ahmet@sirket.com"}},
        },
    ]

    records = build_records(events)

    assert records[0]["user"] == "[EMAIL_1] adresine mail at"
    assert records[0]["output"]["args"]["to"] == "[EMAIL_1]"


def test_load_events_skips_blank_lines(tmp_path):
    input_path = tmp_path / "events.jsonl"
    input_path.write_text(
        '{"request_id": "r1", "step": "extraction"}\n\n'
        '{"request_id": "r1", "step": "tool_execute"}\n',
        encoding="utf-8",
    )

    events = load_events(input_path)

    assert len(events) == 2
