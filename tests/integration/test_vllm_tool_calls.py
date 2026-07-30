"""Canli vLLM sunucusuna karsi calisan entegrasyon testleri. Varsayilan olarak
atlanir; calistirmak icin: pytest -m integration"""

import json

import pytest

from aegis.extraction.candidates import extract_candidates
from aegis.llm import client as llm_client
from aegis.llm.prompt_builder import assemble_request
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
    # Asil kanit: LLM'in dondugu deger candidates disinda BIR SEY OLAMAZ
    # (schema enum kisiti). Bu, bugunku serbest-metin denemesinde gordugumuz
    # halusinasyonun (uydurma path) yapisal olarak imkansiz oldugunu kanitlar.


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
