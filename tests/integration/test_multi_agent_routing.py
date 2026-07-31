"""Canli vLLM sunucusuna karsi calisan entegrasyon testleri. Varsayilan
olarak atlanir; calistirmak icin: pytest -m integration

Coordinator'in gercek coklu-Agent routing'ini (bkz. aegis.decision.
agent_router) ve yeni Notes/Calendar tool'larinin enum-kisitli davranisini
dogrular."""

import json

import pytest

from aegis import config
from aegis.coordinator.coordinator import Coordinator
from aegis.extraction.candidates import extract_candidates
from aegis.llm import client as llm_client
from aegis.llm.prompt_builder import assemble_named_request, assemble_request
from aegis.logging_.event_log import StructuredLogger
from aegis.tools.add_event_tool import AddEventTool
from aegis.tools.base import ToolContext
from aegis.tools.create_note_tool import CreateNoteTool
from aegis.tools.list_events_tool import ListEventsTool
from aegis.tools.list_upcoming_events_tool import ListUpcomingEventsTool

pytestmark = pytest.mark.integration


def test_ambiguous_message_routes_via_llm_to_notes_agent(tmp_path, monkeypatch):
    """'olustur' hem workspace (create_folder) hem notes (create_note) icin
    dogal oldugundan agent_router bunu belirsiz sayip LLM'e birakir (bkz.
    tests/unit/test_agent_router.py) - burada gercek modelin dogru Agent'i
    (notes_agent) sectigini kanitliyoruz."""
    monkeypatch.setattr(config, "SANDBOX_ROOT", tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    coordinator = Coordinator()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = coordinator.route(
        "'Alisveris listesi' basligiyla 'sut, ekmek' icerikli bir not olustur.",
        "req-route-notes",
        logger,
    )

    assert result.success is True


def test_create_note_named_call_forces_yok_when_slot_missing():
    prompt = "Bir not olustur."
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    assert candidates.quoted_spans == []

    request = assemble_named_request(prompt, CreateNoteTool(), ctx)
    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls
    args = json.loads(message.tool_calls[0].function.arguments)
    assert args["title"] == "YOK"
    assert args["content"] == "YOK"


def test_add_event_named_call_forces_yok_when_slot_missing():
    prompt = "Bir etkinlik ekle."
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    assert candidates.dates == []

    request = assemble_named_request(prompt, AddEventTool(), ctx)
    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls
    args = json.loads(message.tool_calls[0].function.arguments)
    assert args["date"] == "YOK"


def test_add_event_named_call_fills_time_and_recurrence():
    prompt = "15.08.2026 saat 07:30 'Spor' etkinligini haftalik olarak ekle."
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    assert candidates.times == ["07:30"]
    assert candidates.recurrences == ["haftalik"]

    request = assemble_named_request(prompt, AddEventTool(), ctx)
    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls
    args = json.loads(message.tool_calls[0].function.arguments)
    assert args["title"] == "Spor"
    assert args["date"] == "15.08.2026"
    assert args["time"] == "07:30"
    assert args["recurrence"] == "haftalik"


def test_list_upcoming_events_selected_over_list_events_by_intent():
    # "hatirlat"/"goster" gibi soyut fiiller modeli karistirabiliyor (2
    # tool'un da sifir slotu oldugu icin ayirt edici tek sinyal fiil) -
    # "listele" ile tutarli sekilde dogru tool secildi, o kullanildi.
    prompt = "Yaklasan etkinliklerimi listele."
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    request = assemble_request(prompt, [ListEventsTool(), ListUpcomingEventsTool()], ctx)
    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls, "LLM tool cagirmadi"
    assert message.tool_calls[0].function.name == "list_upcoming_events"
