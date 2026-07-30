from aegis.extraction.candidates import extract_candidates


def test_folder_and_filename_extraction():
    c = extract_candidates("rapor.pdf dosyasini Arsiv klasorune tasi.")
    assert c.filenames == ["rapor.pdf"]
    assert c.folder_names == ["Arsiv"]
    assert c.quoted_spans == []
    assert c.emails == []


def test_email_and_quoted_extraction():
    text = (
        "ahmet@example.com adresine 'Toplanti' konulu, "
        "'Yarin saat 10da toplanti var' icerikli bir mail gonder."
    )
    c = extract_candidates(text)
    assert c.emails == ["ahmet@example.com"]
    assert c.quoted_spans == ["Toplanti", "Yarin saat 10da toplanti var"]
    # email'in dosya-adi gibi gorunen kismi (example.com) filenames'e sizmamali
    assert "example.com" not in c.filenames


def test_folder_only_reference():
    c = extract_candidates("Indirilenler klasorundeki dosyalari listele.")
    assert c.folder_names == ["Indirilenler"]
    assert c.filenames == []


def test_no_candidates_when_nothing_specific_mentioned():
    c = extract_candidates("Bir dosyayi tasimak istiyorum.")
    assert c.filenames == []
    assert c.folder_names == []
    assert c.quoted_spans == []
    assert c.emails == []


def test_no_tool_relevant_candidates_for_unrelated_prompt():
    c = extract_candidates("Bugun hava nasil?")
    assert c.filenames == []
    assert c.folder_names == []
    assert c.emails == []


def test_dedupe_preserves_order():
    c = extract_candidates("rapor.pdf ve rapor.pdf ayni dosyadir.")
    assert c.filenames == ["rapor.pdf"]
