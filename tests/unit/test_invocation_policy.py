from aegis.decision.invocation_policy import decide
from aegis.tools.base import SlotRequirement


def test_single_unambiguous_candidate_skips_llm():
    slots = [SlotRequirement(slot_name="folder", candidates=["Indirilenler"])]
    decision = decide(slots)
    assert decision.skip_llm is True
    assert decision.auto_resolved == {"folder": "Indirilenler"}


def test_multiple_candidates_requires_llm():
    slots = [SlotRequirement(slot_name="destination", candidates=["Arsiv", "Arsiv2"])]
    decision = decide(slots)
    assert decision.skip_llm is False
    assert decision.auto_resolved is None


def test_zero_candidates_requires_llm():
    slots = [SlotRequirement(slot_name="source", candidates=[])]
    decision = decide(slots)
    assert decision.skip_llm is False


def test_all_slots_must_be_unambiguous():
    slots = [
        SlotRequirement(slot_name="source", candidates=["rapor.pdf"]),
        SlotRequirement(slot_name="destination", candidates=["Arsiv", "Arsiv2"]),
    ]
    decision = decide(slots)
    assert decision.skip_llm is False


def test_optional_slot_with_one_candidate_is_auto_filled():
    required = [SlotRequirement(slot_name="title", candidates=["Spor"])]
    optional = [SlotRequirement(slot_name="time", candidates=["07:30"])]
    decision = decide(required, optional)
    assert decision.skip_llm is True
    assert decision.auto_resolved == {"title": "Spor", "time": "07:30"}


def test_optional_slot_with_no_candidates_is_omitted_not_lost():
    required = [SlotRequirement(slot_name="title", candidates=["Spor"])]
    optional = [SlotRequirement(slot_name="time", candidates=[])]
    decision = decide(required, optional)
    assert decision.skip_llm is True
    assert decision.auto_resolved == {"title": "Spor"}


def test_optional_slot_with_multiple_candidates_requires_llm():
    required = [SlotRequirement(slot_name="title", candidates=["Spor"])]
    optional = [SlotRequirement(slot_name="time", candidates=["07:30", "08:00"])]
    decision = decide(required, optional)
    assert decision.skip_llm is False
    assert decision.auto_resolved is None


def test_no_optional_slots_behaves_like_before():
    required = [SlotRequirement(slot_name="title", candidates=["Spor"])]
    decision = decide(required)
    assert decision.skip_llm is True
    assert decision.auto_resolved == {"title": "Spor"}
