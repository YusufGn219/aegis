"""Ortak orkestrasyon motoru: kullanici mesaji -> deterministik extraction ->
(mumkunse LLM'e hic sormadan otomatik cozum, degilse enum-kisitli LLM
secimi) -> dosya-sistemi slotlari icin PathResolver -> Permission Engine ->
Tool.execute.

Bu akis WorkspaceOrganizerSkill/NotesSkill/CalendarSkill icin BIREBIR
aynidir - tek fark her Skill'in kendi `tools` listesi. Kod tekrarini
onlemek icin akis buraya, `tools`/`skill_name` parametreli tek bir
fonksiyona tasindi; Skill siniflari artik sadece kendi tool listelerini
tanimlayan ince sarmalayicilar."""

from __future__ import annotations

import json

from aegis import config
from aegis.decision import invocation_policy
from aegis.extraction.candidates import extract_candidates
from aegis.llm import client as llm_client
from aegis.llm.prompt_builder import PROMPT_VERSION, assemble_named_request, assemble_request
from aegis.logging_.event_log import LogEvent, StructuredLogger, Timer
from aegis.permission.engine import PermissionEngine
from aegis.resolution.path_resolver import PathResolver, ResolutionStatus, YOK
from aegis.tools.base import Tool, ToolContext, ToolResult

MAX_RESOLUTION_RETRIES = 2


def _serialize_message(message) -> str:
    """LLM'in ham completion mesajini fine-tuning export'u icin JSON metne
    cevirir. Pydantic modeliyse model_dump() kullanilir, degilse str()."""
    try:
        return json.dumps(message.model_dump(), ensure_ascii=False)
    except Exception:
        return str(message)


def _tool_is_fully_evidenced(tool: Tool, ctx: ToolContext) -> bool:
    """Tool'un TUM zorunlu slotlarinda en az 1 aday varsa 'tam kanitlanmis'
    sayilir. Not: aynı aday havuzunu (orn. folder_names) birden fazla tool
    paylasabilir (list_files.folder ve move_file.destination gibi) - bu
    yuzden tek basina yeterli degil, bkz. asagidaki 'en spesifik tool' secimi."""
    slots = tool.required_slots(ctx)
    return bool(slots) and all(len(slot.candidates) > 0 for slot in slots)


def run_tool_selection(
    user_message: str,
    request_id: str,
    logger: StructuredLogger,
    tools: list[Tool],
    skill_name: str,
    permission_engine: PermissionEngine,
    session_id: str | None = None,
    turn_index: int | None = None,
) -> ToolResult:
    # 1) Deterministik extraction - LLM yok.
    with Timer() as t:
        candidates = extract_candidates(user_message)
    logger.log(
        LogEvent(
            request_id=request_id,
            step="extraction",
            skill=skill_name,
            duration_ms=t.duration_ms,
            decision="candidates extracted",
            success=True,
            extra={"candidates": vars(candidates)},
            raw_user_message=user_message,
            session_id=session_id,
            turn_index=turn_index,
        )
    )

    ctx = ToolContext(sandbox_root=str(config.SANDBOX_ROOT), candidates=candidates)

    # 2-4) Tum zorunlu slotlari dolu olan ("tam kanitlanmis") tool'lar
    # arasindan EN COK slot dolduran (en spesifik) tool tek basina one
    # cikiyorsa, LLM'e hic sormadan otomatik coz. Birden fazla tool ayni
    # spesifiklikte kanitlanmissa (gercek belirsizlik) LLM'e birakilir.
    fully_evidenced = [t for t in tools if _tool_is_fully_evidenced(t, ctx)]

    tool: Tool | None = None
    raw_args: dict = {}
    llm_invoked = False
    tokens_prompt = None
    tokens_completion = None

    if fully_evidenced:
        max_slot_count = max(len(t.required_slots(ctx)) for t in fully_evidenced)
        most_specific = [t for t in fully_evidenced if len(t.required_slots(ctx)) == max_slot_count]
        if len(most_specific) == 1:
            candidate_tool = most_specific[0]
            decision = invocation_policy.decide(
                candidate_tool.required_slots(ctx), candidate_tool.optional_slots(ctx)
            )
            logger.log(
                LogEvent(
                    request_id=request_id,
                    step="invocation_decision",
                    skill=skill_name,
                    tool=candidate_tool.name,
                    llm_invoked=not decision.skip_llm,
                    decision=decision.reason,
                    success=True,
                    extra={"auto_resolved": decision.auto_resolved},
                    raw_user_message=user_message,
                    session_id=session_id,
                    turn_index=turn_index,
                )
            )
            if decision.skip_llm:
                tool = candidate_tool
                raw_args = decision.auto_resolved or {}

    if tool is None:
        # Belirsizlik var (birden fazla tool'a dair kanit, ya da tek
        # tool'un slotlarinda 2+/0 aday) -> LLM'e enum-kisitli semayla sor.
        llm_invoked = True
        request = assemble_request(user_message, tools, ctx)
        with Timer() as t:
            response = llm_client.call_for_tool_selection(request)
        tokens_prompt = getattr(response.usage, "prompt_tokens", None)
        tokens_completion = getattr(response.usage, "completion_tokens", None)
        message = response.choices[0].message

        if not message.tool_calls:
            logger.log(
                LogEvent(
                    request_id=request_id,
                    step="llm_call",
                    skill=skill_name,
                    llm_invoked=True,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    duration_ms=t.duration_ms,
                    decision="LLM tool cagirmadi (red/netlestirme)",
                    success=True,
                    raw_user_message=user_message,
                    system_prompt=request["messages"][0]["content"],
                    prompt_version=PROMPT_VERSION,
                    tool_schemas_sent=request["tools"],
                    raw_completion=_serialize_message(message),
                    session_id=session_id,
                    turn_index=turn_index,
                )
            )
            return ToolResult(success=False, message=message.content or "(bos yanit)")

        tool_call = message.tool_calls[0]
        tool = next((c for c in tools if c.name == tool_call.function.name), None)
        try:
            raw_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            raw_args = {}

        logger.log(
            LogEvent(
                request_id=request_id,
                step="llm_call",
                skill=skill_name,
                tool=tool.name if tool else tool_call.function.name,
                llm_invoked=True,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                duration_ms=t.duration_ms,
                decision="LLM tool secti (auto, semasiz)",
                success=tool is not None,
                extra={"phase": "tool_selection", "raw_args": raw_args},
                raw_user_message=user_message,
                system_prompt=request["messages"][0]["content"],
                prompt_version=PROMPT_VERSION,
                tool_schemas_sent=request["tools"],
                raw_completion=_serialize_message(message),
                session_id=session_id,
                turn_index=turn_index,
            )
        )

        if tool is not None:
            # tool_choice="auto" ile guided decoding UYGULANMAZ (vLLM
            # 0.26.0'da dogrulandi, bkz. prompt_builder.py docstring) -
            # yukaridaki raw_args enum disina cikmis olabilir. Simdi ayni
            # tool icin ISIMLENDIRILMIS tool_choice ile ikinci bir cagri
            # yapip argumanlari GERCEKTEN enum-kisitli uretiyoruz.
            named_request = assemble_named_request(user_message, tool, ctx)
            with Timer() as t2:
                named_response = llm_client.call_for_tool_selection(named_request)
            named_tokens_prompt = getattr(named_response.usage, "prompt_tokens", None)
            named_tokens_completion = getattr(named_response.usage, "completion_tokens", None)
            named_message = named_response.choices[0].message

            if named_message.tool_calls:
                try:
                    raw_args = json.loads(named_message.tool_calls[0].function.arguments)
                except json.JSONDecodeError:
                    raw_args = {}

            logger.log(
                LogEvent(
                    request_id=request_id,
                    step="llm_call",
                    skill=skill_name,
                    tool=tool.name,
                    llm_invoked=True,
                    tokens_prompt=named_tokens_prompt,
                    tokens_completion=named_tokens_completion,
                    duration_ms=t2.duration_ms,
                    decision="LLM argumanlari sema-kisitli uretti (named)",
                    success=bool(named_message.tool_calls),
                    extra={"phase": "argument_binding", "raw_args": raw_args},
                    raw_user_message=user_message,
                    system_prompt=named_request["messages"][0]["content"],
                    prompt_version=PROMPT_VERSION,
                    tool_schemas_sent=named_request["tools"],
                    raw_completion=_serialize_message(named_message),
                    session_id=session_id,
                    turn_index=turn_index,
                )
            )

    if tool is None:
        return ToolResult(success=False, message="LLM bilinmeyen bir tool secti.")

    # 5) Dosya-sistemi tipi slotlari gercek path'lere coz.
    slot_by_name = {s.slot_name: s for s in tool.required_slots(ctx)}
    resolver = PathResolver(str(config.SANDBOX_ROOT))
    resolved_args: dict = {}

    for slot_name, value in raw_args.items():
        slot = slot_by_name.get(slot_name)
        if slot is None or not slot.is_filesystem_path:
            resolved_args[slot_name] = None if value == YOK else value
            continue

        resolved_value = _resolve_with_retries(resolver, slot_name, value, request_id, logger)
        if resolved_value is None and value != YOK:
            return ToolResult(
                success=False,
                message=f"'{slot_name}' icin gecerli bir konum bulunamadi, istek iptal edildi.",
            )
        resolved_args[slot_name] = resolved_value

    # 6) Permission Engine.
    permitted = permission_engine.check_and_confirm(tool, resolved_args)
    logger.log(
        LogEvent(
            request_id=request_id,
            step="permission",
            skill=skill_name,
            tool=tool.name,
            llm_invoked=llm_invoked,
            decision="onaylandi" if permitted else "reddedildi",
            success=permitted,
            session_id=session_id,
            turn_index=turn_index,
        )
    )
    if not permitted:
        return ToolResult(success=False, message="Kullanici onayi vermedi.")

    # 7) Tool'u calistir.
    with Timer() as t:
        result = tool.execute(resolved_args, ctx)
    logger.log(
        LogEvent(
            request_id=request_id,
            step="tool_execute",
            skill=skill_name,
            tool=tool.name,
            llm_invoked=llm_invoked,
            duration_ms=t.duration_ms,
            decision=result.message,
            success=result.success,
            session_id=session_id,
            turn_index=turn_index,
        )
    )
    return result


def _resolve_with_retries(
    resolver: PathResolver,
    slot_name: str,
    value: str,
    request_id: str,
    logger: StructuredLogger,
) -> str | None:
    current_value = value
    for attempt in range(MAX_RESOLUTION_RETRIES + 1):
        resolution = resolver.resolve(current_value)
        logger.log(
            LogEvent(
                request_id=request_id,
                step="path_resolution",
                decision=f"{slot_name}={current_value!r} -> {resolution.status.value}",
                success=resolution.status == ResolutionStatus.RESOLVED,
                extra={"matches": resolution.matches},
            )
        )
        if resolution.status == ResolutionStatus.NOT_NEEDED:
            return None
        if resolution.status == ResolutionStatus.RESOLVED:
            return resolution.resolved_path
        if attempt >= MAX_RESOLUTION_RETRIES:
            return None
        if resolution.status == ResolutionStatus.AMBIGUOUS:
            print(f"\n'{current_value}' icin birden fazla eslesme bulundu:")
            for m in resolution.matches:
                print(f"    {m}")
        else:
            print(f"\n'{current_value}' bulunamadi.")
        current_value = input(f"'{slot_name}' icin tam ismi yazin: ").strip()
    return None
