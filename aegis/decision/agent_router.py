"""Mesaji hangi Agent'in (workspace/notes/calendar) ele alacagina
deterministik olarak karar verir - "minimum LLM" ilkesiyle:
tam 1 Agent'in anahtar kelimeleri eslesirse LLM'e hic sorulmadan o Agent'a
gidilir (invocation_policy'nin "tam 1 aday varsa LLM atlanir" felsefesiyle
ayni). 0 eslesme -> guvenli varsayilan workspace_agent (bugunku davranis
zaten alakasiz istekleri "tool cagrilmadi" ile karsiliyor). 2+ eslesme ->
gercek belirsizlik, Coordinator kucuk bir isimlendirilmis LLM cagrisiyla
karar verir."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aegis.extraction.candidates import normalize

WORKSPACE_AGENT = "workspace_agent"
NOTES_AGENT = "notes_agent"
CALENDAR_AGENT = "calendar_agent"

ALL_AGENTS = [WORKSPACE_AGENT, NOTES_AGENT, CALENDAR_AGENT]

_AGENT_KEYWORDS: dict[str, list[str]] = {
    WORKSPACE_AGENT: [
        "dosya",
        "klasor",
        "folder",
        "directory",
        "tasi",
        "move",
        "kopyala",
        "copy",
        "sil",
        "delete",
        "listele",
        "list files",
        "olustur",
        "mail",
        "e-posta",
        "eposta",
        "email",
        "gonder",
    ],
    NOTES_AGENT: ["not", "notlar", "hatirlatma", "note", "reminder"],
    CALENDAR_AGENT: [
        "takvim",
        "etkinlik",
        # "etkinlik" unluyle baslayan ek aldiginda unsuz yumusamasina ugrar
        # (k -> g): "etkinligi"/"etkinligini"/"etkinlige" gibi CEKIMLI
        # bicimlerde kok "etkinlik" DEGIL "etkinlig" olarak gecer - salt
        # sol-sinirli prefix esleseme bunu YAKALAMAZ, ayrica eklendi.
        "etkinlig",
        "toplanti",
        "randevu",
        "calendar",
        "event",
        "appointment",
    ],
}

_AGENT_PATTERNS: dict[str, re.Pattern] = {
    # SADECE sol kelime siniri (\b<kok>) - saga sinir YOK, cunku Turkce
    # eklemeli bir dil: "klasor" koku "klasorundeki"/"klasore" gibi cekimli
    # bicimlerin ICINDE gecer, tam kelime esitligi ("klasor\b") bu cekimli
    # bicimlerin HICBIRINI yakalamaz. Bu, ornegin Ingilizce "not" gibi kisa
    # koklerin baska kelimelerin (orn. "notebook") ONEKI olarak da eslesmesi
    # riskini goze alir - bu tradeoff, Turkce cekim kapsamasi icin kabul edildi.
    agent_name: re.compile(r"\b(?:" + "|".join(re.escape(kw) for kw in keywords) + r")")
    for agent_name, keywords in _AGENT_KEYWORDS.items()
}


@dataclass
class RoutingDecision:
    agent_name: str | None
    skip_llm: bool
    reason: str
    matched_agents: list[str]


def decide(user_message: str) -> RoutingDecision:
    normalized = normalize(user_message)
    matched = [
        agent_name for agent_name, pattern in _AGENT_PATTERNS.items() if pattern.search(normalized)
    ]

    if len(matched) == 1:
        return RoutingDecision(
            agent_name=matched[0],
            skip_llm=True,
            reason=f"Tek agent'in anahtar kelimesi eslesti ({matched[0]}) -> LLM atlandi.",
            matched_agents=matched,
        )

    if len(matched) == 0:
        return RoutingDecision(
            agent_name=WORKSPACE_AGENT,
            skip_llm=True,
            reason="Hicbir agent'in anahtar kelimesi eslesmedi -> varsayilan workspace_agent.",
            matched_agents=matched,
        )

    return RoutingDecision(
        agent_name=None,
        skip_llm=False,
        reason=f"{len(matched)} agent'in anahtar kelimesi eslesti ({matched}) -> LLM karar verecek.",
        matched_agents=matched,
    )
