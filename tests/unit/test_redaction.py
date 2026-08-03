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


def test_filename_is_replaced_when_provided():
    record = {
        "user": "rapor.pdf dosyasini Arsiv klasorune tasi",
        "output": {"args": {"source": "rapor.pdf"}},
    }
    result = redact_record(record, filenames=["rapor.pdf"])
    assert result["user"] == "[FILENAME_1] dosyasini Arsiv klasorune tasi"
    assert result["output"]["args"]["source"] == "[FILENAME_1]"


def test_folder_name_is_replaced_when_provided():
    record = {
        "user": "rapor.pdf dosyasini Arsiv klasorune tasi",
        "output": {"args": {"destination": "Arsiv"}},
    }
    result = redact_record(record, folder_names=["Arsiv"])
    assert result["user"] == "rapor.pdf dosyasini [FOLDER_1] klasorune tasi"
    assert result["output"]["args"]["destination"] == "[FOLDER_1]"


def test_filenames_and_folder_names_without_hint_are_not_guessed():
    record = {"user": "rapor.pdf dosyasini Arsiv klasorune tasi"}
    result = redact_record(record)
    assert result == record


def test_multiple_categories_combined_with_independent_numbering():
    record = {
        "user": "ahmet@sirket.com adresine rapor.pdf dosyasini Arsiv klasorunden gonder",
        "output": {"args": {"to": "ahmet@sirket.com", "source": "rapor.pdf", "folder": "Arsiv"}},
    }
    result = redact_record(record, filenames=["rapor.pdf"], folder_names=["Arsiv"])
    assert "[EMAIL_1]" in result["user"]
    assert "[FILENAME_1]" in result["user"]
    assert "[FOLDER_1]" in result["user"]
    assert result["output"]["args"] == {
        "to": "[EMAIL_1]",
        "source": "[FILENAME_1]",
        "folder": "[FOLDER_1]",
    }


def test_longer_filename_does_not_get_partially_matched_by_shorter_one():
    record = {"user": "rapor.pdf.bak dosyasini rapor.pdf ile karsilastir"}
    result = redact_record(record, filenames=["rapor.pdf", "rapor.pdf.bak"])
    assert result["user"] == "[FILENAME_2] dosyasini [FILENAME_1] ile karsilastir"
