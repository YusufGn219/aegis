from aegis.redaction import redact_record


def test_no_email_leaves_record_unchanged():
    record = {"user": "Arsiv klasorunu listele", "output": {"tool": "list_files"}}
    assert redact_record(record) == record


def test_single_email_is_replaced_with_placeholder():
    record = {"user": "ahmet@sirket.com adresine mail at", "output": None}
    result = redact_record(record)
    assert result["user"] == "[EMAIL_1] adresine mail at"


def test_same_email_gets_same_placeholder_across_fields():
    record = {
        "user": "ahmet@sirket.com adresine mail at",
        "output": {"tool": "send_email", "args": {"to": "ahmet@sirket.com"}},
    }
    result = redact_record(record)
    assert result["user"] == "[EMAIL_1] adresine mail at"
    assert result["output"]["args"]["to"] == "[EMAIL_1]"


def test_different_emails_get_different_placeholders():
    record = {
        "user": "ahmet@sirket.com ve mehmet@sirket.com adreslerine mail at",
        "output": {"args": {"to": "ahmet@sirket.com", "cc": "mehmet@sirket.com"}},
    }
    result = redact_record(record)
    assert "[EMAIL_1]" in result["user"]
    assert "[EMAIL_2]" in result["user"]
    assert result["output"]["args"]["to"] == "[EMAIL_1]"
    assert result["output"]["args"]["cc"] == "[EMAIL_2]"


def test_email_inside_raw_completion_string_is_replaced():
    record = {
        "user": "ahmet@sirket.com adresine mail at",
        "output": '{"tool_calls":[{"function":{"arguments":"{\\"to\\":\\"ahmet@sirket.com\\"}"}}]}',
    }
    result = redact_record(record)
    assert "ahmet@sirket.com" not in result["output"]
    assert "[EMAIL_1]" in result["output"]


def test_non_email_fields_pass_through_untouched():
    record = {"request_id": "r1", "label": "unlabeled", "tools": None}
    assert redact_record(record) == record
