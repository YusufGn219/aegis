from aegis.decision import agent_router


def test_single_workspace_keyword_skips_llm():
    decision = agent_router.decide("rapor.pdf dosyasini Arsiv klasorune tasi.")
    assert decision.skip_llm is True
    assert decision.agent_name == agent_router.WORKSPACE_AGENT


def test_single_notes_keyword_skips_llm():
    # "olustur" bilerek kullanilmiyor - hem workspace'in (create_folder) hem
    # notes'un (create_note) dogal fiili, bu yuzden gercek bir belirsizlik
    # yaratir (bkz. test_multiple_domain_keywords_requires_llm).
    decision = agent_router.decide("'Alisveris listesi' basligiyla bir not yaz.")
    assert decision.skip_llm is True
    assert decision.agent_name == agent_router.NOTES_AGENT


def test_single_calendar_keyword_skips_llm():
    decision = agent_router.decide("15.08.2026 tarihine bir etkinlik ekle.")
    assert decision.skip_llm is True
    assert decision.agent_name == agent_router.CALENDAR_AGENT


def test_no_keyword_match_defaults_to_workspace():
    decision = agent_router.decide("Bugun hava nasil?")
    assert decision.skip_llm is True
    assert decision.agent_name == agent_router.WORKSPACE_AGENT
    assert decision.matched_agents == []


def test_multiple_domain_keywords_requires_llm():
    decision = agent_router.decide("Arsiv klasorune tasi ve bir not olustur.")
    assert decision.skip_llm is False
    assert decision.agent_name is None
    assert set(decision.matched_agents) == {agent_router.WORKSPACE_AGENT, agent_router.NOTES_AGENT}


def test_english_keyword_variants_match():
    decision = agent_router.decide("add a new calendar event for tomorrow")
    assert decision.skip_llm is True
    assert decision.agent_name == agent_router.CALENDAR_AGENT


def test_accent_insensitive_matching():
    decision = agent_router.decide("Bir hatirlatma yap.")
    assert decision.agent_name == agent_router.NOTES_AGENT


def test_consonant_softening_inflected_form_matches():
    # "etkinlik" + unluyle baslayan ek -> unsuz yumusamasi (k -> g):
    # "etkinligini" koku "etkinlik" DEGIL "etkinlig" icerir.
    decision = agent_router.decide(
        "15.08.2026 saat 07:30 'Spor' etkinligini haftalik olarak ekle."
    )
    assert decision.skip_llm is True
    assert decision.agent_name == agent_router.CALENDAR_AGENT
