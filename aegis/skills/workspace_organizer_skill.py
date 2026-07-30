"""Uctan uca akis: kullanici mesaji -> deterministik extraction -> (mumkunse
LLM'e hic sormadan otomatik cozum, degilse enum-kisitli LLM secimi) ->
dosya-sistemi slotlari icin PathResolver -> Permission Engine -> Tool.execute.

Bu, bugunku vLLM_projects/scripts/tool_call_test.py prototipinde dogrulanan
akisin gercek, tekrar kullanilabilir kod haline getirilmis versiyonudur."""

from __future__ import annotations

import json

from aegis import config
from aegis.decision import invocation_policy
from aegis.extraction.candidates import extract_candidates
from aegis.llm import client as llm_client
from aegis.llm.prompt_builder import assemble_request
from aegis.logging_.event_log import LogEvent, StructuredLogger, Timer
from aegis.permission.engine import PermissionEngine
from aegis.resolution.path_resolver import PathResolver, ResolutionStatus, YOK
from aegis.skills.base import Skill
from aegis.tools.base import Tool, ToolContext, ToolResult
from aegis.tools.list_files_tool import ListFilesTool
from aegis.tools.move_file_tool import MoveFileTool
from aegis.tools.send_email_tool import SendEmailTool

MAX_RESOLUTION_RETRIES = 2


def _tool_is_fully_evidenced(tool: Tool, ctx: ToolContext) -> bool:
    """Tool'un TUM zorunlu slotlarinda en az 1 aday varsa 'tam kanitlanmis'
    sayilir. Not: aynı aday havuzunu (orn. folder_names) birden fazla tool
    paylasabilir (list_files.folder ve move_file.destination gibi) - bu
    yuzden tek basina yeterli degil, bkz. asagidaki 'en spesifik tool' secimi."""
    slots = tool.required_slots(ctx)
    return bool(slots) and all(len(slot.candidates) > 0 for slot in slots)


class WorkspaceOrganizerSkill(Skill):
    name = "workspace_organizer"

    def __init__(self):
        self.tools: list[Tool] = [ListFilesTool(), MoveFileTool(), SendEmailTool()]
        self.permission_engine = PermissionEngine()

    def run(self, user_message: str, request_id: str, logger: StructuredLogger) -> ToolResult:
        # 1) Deterministik extraction - LLM yok.
        with Timer() as t:
            candidates = extract_candidates(user_message)
        logger.log(
            LogEvent(
                request_id=request_id,
                step="extraction",
                skill=self.name,
                duration_ms=t.duration_ms,
                decision="candidates extracted",
                success=True,
                extra={"candidates": vars(candidates)},
            )
        )

        ctx = ToolContext(sandbox_root=str(config.SANDBOX_ROOT), candidates=candidates)

        # 2-4) Tum zorunlu slotlari dolu olan ("tam kanitlanmis") tool'lar
        # arasindan EN COK slot dolduran (en spesifik) tool tek basina one
        # cikiyorsa, LLM'e hic sormadan otomatik coz. Birden fazla tool ayni
        # spesifiklikte kanitlanmissa (gercek belirsizlik) LLM'e birakilir.
        fully_evidenced = [t for t in self.tools if _tool_is_fully_evidenced(t, ctx)]

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
                decision = invocation_policy.decide(candidate_tool.required_slots(ctx))
                logger.log(
                    LogEvent(
                        request_id=request_id,
                        step="invocation_decision",
                        skill=self.name,
                        tool=candidate_tool.name,
                        llm_invoked=not decision.skip_llm,
                        decision=decision.reason,
                        success=True,
                    )
                )
                if decision.skip_llm:
                    tool = candidate_tool
                    raw_args = decision.auto_resolved or {}

        if tool is None:
            # Belirsizlik var (birden fazla tool'a dair kanit, ya da tek
            # tool'un slotlarinda 2+/0 aday) -> LLM'e enum-kisitli semayla sor.
            llm_invoked = True
            request = assemble_request(user_message, self.tools, ctx)
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
                        skill=self.name,
                        llm_invoked=True,
                        tokens_prompt=tokens_prompt,
                        tokens_completion=tokens_completion,
                        duration_ms=t.duration_ms,
                        decision="LLM tool cagirmadi (red/netlestirme)",
                        success=True,
                    )
                )
                return ToolResult(success=False, message=message.content or "(bos yanit)")

            tool_call = message.tool_calls[0]
            tool = next((c for c in self.tools if c.name == tool_call.function.name), None)
            try:
                raw_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                raw_args = {}

            logger.log(
                LogEvent(
                    request_id=request_id,
                    step="llm_call",
                    skill=self.name,
                    tool=tool.name if tool else tool_call.function.name,
                    llm_invoked=True,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    duration_ms=t.duration_ms,
                    decision="LLM tool secti",
                    success=tool is not None,
                    extra={"raw_args": raw_args},
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

            resolved_value = self._resolve_with_retries(resolver, slot_name, value, request_id, logger)
            if resolved_value is None and value != YOK:
                return ToolResult(
                    success=False,
                    message=f"'{slot_name}' icin gecerli bir konum bulunamadi, istek iptal edildi.",
                )
            resolved_args[slot_name] = resolved_value

        # 6) Permission Engine.
        permitted = self.permission_engine.check_and_confirm(tool, resolved_args)
        logger.log(
            LogEvent(
                request_id=request_id,
                step="permission",
                skill=self.name,
                tool=tool.name,
                llm_invoked=llm_invoked,
                decision="onaylandi" if permitted else "reddedildi",
                success=permitted,
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
                skill=self.name,
                tool=tool.name,
                llm_invoked=llm_invoked,
                duration_ms=t.duration_ms,
                decision=result.message,
                success=result.success,
            )
        )
        return result

    def _resolve_with_retries(
        self,
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
