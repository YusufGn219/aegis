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
