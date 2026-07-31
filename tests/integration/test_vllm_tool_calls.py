"""Canli vLLM sunucusuna karsi calisan entegrasyon testleri. Varsayilan olarak
atlanir; calistirmak icin: pytest -m integration

Iki katman test edilir:
1. tool_choice="auto" (assemble_request) - HANGI tool'un (varsa) uygun
   oldugunu belirler. Bu modda guided decoding UYGULANMAZ (vLLM 0.26.0'da
   dogrulandi) - asagidaki testler modelin PRATIKTE dogru tool/degerleri
   sectigini gosterir, ama bu bir yapisal garanti DEGILDIR.
2. ISIMLENDIRILMIS tool_choice (assemble_named_request) - secilen tool icin
   argumanlarin GERCEKTEN enum-kisitli uretildigini kanitlar. Asil
   halusinasyon-onleme garantisi buradadir; workspace_organizer_skill.py bu
   iki asamayi zincirleyerek kullanir."""

import json

import pytest

from aegis import config
from aegis.extraction.candidates import extract_candidates
from aegis.llm import client as llm_client
from aegis.llm.prompt_builder import assemble_named_request, assemble_request
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.workspace_organizer_skill import WorkspaceOrganizerSkill
from aegis.tools.base import ToolContext
from aegis.tools.list_files_tool import ListFilesTool
from aegis.tools.move_file_tool import MoveFileTool
from aegis.tools.send_email_tool import SendEmailTool

pytestmark = pytest.mark.integration


def _all_tools():
    return [ListFilesTool(), MoveFileTool(), SendEmailTool()]


def test_move_file_enum_constrained_no_hallucination():
    prompt = "rapor.pdf dosyasini Arsiv klasorune tasi."
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    request = assemble_request(prompt, _all_tools(), ctx)

    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls, "LLM tool cagirmadi"
    tool_call = message.tool_calls[0]
    assert tool_call.function.name == "move_file"

    args = json.loads(tool_call.function.arguments)
    assert args["source"] in candidates.filenames + ["YOK"]
    assert args["destination"] in candidates.folder_names + ["YOK"]
    # Not: bu, tool_choice="auto" oldugu icin YAPISAL bir garanti degil -
    # sadece modelin bu ornekte candidates icinden dogru secim yaptigini
    # gosterir. Yapisal garanti icin bkz. test_named_call_forces_yok_when_slot_missing.


def test_send_email_verbatim_content():
    prompt = (
        "ahmet@example.com adresine 'Toplanti' konulu, "
        "'Yarin saat 10da toplanti var' icerikli bir mail gonder."
    )
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    request = assemble_request(prompt, _all_tools(), ctx)

    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls
    tool_call = message.tool_calls[0]
    assert tool_call.function.name == "send_email"

    args = json.loads(tool_call.function.arguments)
    assert args["to"] == "ahmet@example.com"
    assert args["subject"] in candidates.quoted_spans
    assert args["body"] in candidates.quoted_spans


def test_ambiguous_request_returns_no_tool_call():
    prompt = "Bugun hava nasil?"
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    request = assemble_request(prompt, _all_tools(), ctx)

    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert not message.tool_calls, "Alakasiz istekte LLM tool cagirmamali"


def test_named_call_forces_yok_when_slot_missing():
    """assemble_request (auto) modda model enum disina cikip dosya adi
    uydurabiliyor (bu vLLM surumunde auto icin guided decoding yok). Asil
    garanti assemble_named_request (isimlendirilmis tool_choice) ile gelir:
    o modda enum GERCEKTEN zorlanir, dosya adi mesajda hic gecmedigi icin
    'source' icin enum tek elemanli (['YOK']) olur ve model baska bir sey
    uretemez."""
    prompt = "Bir dosyayi Arsiv klasorune tasi."
    candidates = extract_candidates(prompt)
    ctx = ToolContext(sandbox_root="workspace_sandbox", candidates=candidates)
    assert candidates.filenames == []  # on-kosul: enum'da YOK'tan baska secenek yok

    request = assemble_named_request(prompt, MoveFileTool(), ctx)
    response = llm_client.call_for_tool_selection(request)
    message = response.choices[0].message

    assert message.tool_calls
    args = json.loads(message.tool_calls[0].function.arguments)
    assert args["source"] == "YOK"


def test_skill_two_step_flow_prevents_hallucinated_move(tmp_path, monkeypatch):
    """workspace_organizer_skill.py'nin gercekte kullandigi iki asamali
    (auto -> named) akisin uctan uca, sahte olmayan bir vLLM cagrisiyla
    dogru sonuca (hicbir dosya tasinmadan basarisiz donus) ulastigini
    dogrular.

    Prompt bilerek IKI farkli klasor adi iceriyor: bu, list_files.folder
    slotunu 2 adayli (belirsiz) yapar, invocation_policy.decide() bu yuzden
    skip_llm=False doner ve akis genel (tum tool'lari iceren) LLM dalina
    duser - move_file de aday havuzuna girer, ama dosya adi hic
    belirtilmedigi icin 'source' enum'u sadece ['YOK'] olur."""
    sandbox = tmp_path
    (sandbox / "Arsiv").mkdir()
    (sandbox / "Yedek").mkdir()
    monkeypatch.setattr(config, "SANDBOX_ROOT", sandbox)

    skill = WorkspaceOrganizerSkill()
    logger = StructuredLogger(path=str(tmp_path / "events.jsonl"))
    result = skill.run(
        "Bir dosyayi Arsiv klasorune ya da Yedek klasorune tasi.", "req-yok", logger
    )

    assert result.success is False
