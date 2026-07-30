"""LLM'e hic sormadan slot-degerlerinin deterministik olarak cozulup
cozulemeyecegine karar verir. Bu politika SADECE zaten secilmis bir tool'un
slot degerlerini kapsar - HANGI tool'un cagrilacagi karari her zaman LLM'e
aittir (kullanicinin 'LLM secim yapsin' ilkesiyle uyumlu)."""

from __future__ import annotations

from dataclasses import dataclass

from aegis.tools.base import SlotRequirement


@dataclass
class InvocationDecision:
    skip_llm: bool
    auto_resolved: dict[str, str] | None
    reason: str


def decide(required_slots: list[SlotRequirement]) -> InvocationDecision:
    """Bir tool'un TUM zorunlu slotlarinda tam olarak 1 gercek aday varsa
    (0 veya 2+ degil), LLM'e sormadan otomatik cozulur. Aksi halde LLM
    cagrisi gerekir (belirsizlik ya da gercek eksiklik var demektir)."""
    auto_resolved: dict[str, str] = {}
    for slot in required_slots:
        if len(slot.candidates) != 1:
            return InvocationDecision(
                skip_llm=False,
                auto_resolved=None,
                reason=(
                    f"'{slot.slot_name}' slotunda {len(slot.candidates)} aday var "
                    "(tam olarak 1 olmali) -> LLM cagrisi gerekli."
                ),
            )
        auto_resolved[slot.slot_name] = slot.candidates[0]

    return InvocationDecision(
        skip_llm=True,
        auto_resolved=auto_resolved,
        reason="Tum zorunlu slotlarda tam olarak 1 belirsizsiz aday var -> LLM atlandi.",
    )
