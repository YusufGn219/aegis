from aegis.extraction.candidates import extract_candidates, normalize


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


def test_english_folder_pattern_extraction():
    c = extract_candidates("list files in the Downloads folder")
    assert c.folder_names == ["Downloads"]


def test_english_directory_pattern_extraction():
    c = extract_candidates("move rapor.pdf to the Archive directory")
    assert c.folder_names == ["Archive"]


def test_normalize_strips_turkish_accents():
    assert normalize("Arşiv") == normalize("Arsiv") == "arsiv"


def test_turkish_and_english_folder_mentions_dedupe_independently():
    c = extract_candidates("Arsiv klasorune tasi, sonra Downloads folder icindekileri listele.")
    assert c.folder_names == ["Arsiv", "Downloads"]


def test_date_and_time_extraction():
    # Not: "07:30'da" gibi Turkce kesme-eki kalibi kasitli KULLANILMIYOR -
    # QUOTED_RE'nin kesme isaretini tirnak sanip yanlis eslesmesine yol
    # aciyor (bilinen, bu degisiklikle ilgisiz bir extraction sinirlamasi).
    c = extract_candidates("15.08.2026 saat 07:30 'Spor' etkinligi ekle.")
    assert c.dates == ["15.08.2026"]
    assert c.times == ["07:30"]
    assert c.quoted_spans == ["Spor"]


def test_recurrence_extraction_daily_weekly_monthly():
    assert extract_candidates("Her gun spor yap.").recurrences == ["gunluk"]
    assert extract_candidates("Haftalik toplanti ekle.").recurrences == ["haftalik"]
    assert extract_candidates("Her ay fatura ode.").recurrences == ["aylik"]


def test_no_recurrence_when_not_mentioned():
    c = extract_candidates("15.08.2026 tarihinde 'Toplanti' etkinligi ekle.")
    assert c.recurrences == []
    assert c.times == []
