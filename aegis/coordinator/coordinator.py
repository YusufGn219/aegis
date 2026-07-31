"""Mesaji hangi Agent'in ele alacagina karar verir. Routing "minimum LLM"
ilkesiyle calisir: aegis.decision.agent_router.decide() tam 1 Agent'in
anahtar kelimesi eslesirse (ya da hic eslesmezse, varsayilan workspace_agent
ile) LLM'e HIC sormadan karar verir; sadece gercek belirsizlikte (2+ Agent
eslesirse) kucuk, isimlendirilmis (guided-decoding zorlanmis) bir LLM
cagrisi yapilir."""

from __future__ import annotations

import json
import uuid

from aegis.agents.base import Agent
from aegis.agents.calendar_agent import CalendarAgent
from aegis.agents.notes_agent import NotesAgent
from aegis.agents.workspace_agent import WorkspaceAgent
from aegis.decision import agent_router
from aegis.llm import client as llm_client
from aegis.llm.prompt_builder import assemble_routing_request
from aegis.logging_.event_log import LogEvent, StructuredLogger
from aegis.tools.base import ToolResult


class Coordinator:
    def __init__(self):
        self.agents: dict[str, Agent] = {
            "workspace_agent": WorkspaceAgent(),
            "notes_agent": NotesAgent(),
            "calendar_agent": CalendarAgent(),
        }
        # Coordinator, bir CLI/proses omrunun tamamini tek bir "oturum"
        # sayar; her route() cagrisi o oturumun bir sonraki turu olur.
        # Fine-tuning verisinde multi-turn baglami korumak icin (bkz.
        # aegis.logging_.event_log.LogEvent.session_id/turn_index).
        self.session_id = str(uuid.uuid4())
        self._turn_index = 0

    def route(self, user_message: str, request_id: str, logger: StructuredLogger) -> ToolResult:
        turn_index = self._turn_index
        self._turn_index += 1
        logger.log(
            LogEvent(
                request_id=request_id,
                step="session_start",
                decision="turn basladi",
                success=True,
                raw_user_message=user_message,
                session_id=self.session_id,
                turn_index=turn_index,
            )
        )

        decision = agent_router.decide(user_message)
        agent_name = decision.agent_name

        if decision.skip_llm:
            logger.log(
                LogEvent(
                    request_id=request_id,
                    step="invocation_decision",
                    decision=decision.reason,
                    llm_invoked=False,
                    success=True,
                    extra={"routed_to": agent_name, "matched_agents": decision.matched_agents},
                    raw_user_message=user_message,
                    session_id=self.session_id,
                    turn_index=turn_index,
                )
            )
        else:
            request = assemble_routing_request(user_message, agent_router.ALL_AGENTS)
            response = llm_client.call_for_tool_selection(request)
            message = response.choices[0].message
            if message.tool_calls:
                args = json.loads(message.tool_calls[0].function.arguments)
                agent_name = args.get("agent")
            logger.log(
                LogEvent(
                    request_id=request_id,
                    step="invocation_decision",
                    decision=decision.reason,
                    llm_invoked=True,
                    success=agent_name in self.agents,
                    extra={"routed_to": agent_name, "matched_agents": decision.matched_agents},
                    raw_user_message=user_message,
                    system_prompt=request["messages"][0]["content"],
                    session_id=self.session_id,
                    turn_index=turn_index,
                )
            )

        agent = self.agents.get(agent_name, self.agents["workspace_agent"])
        return agent.handle(user_message, request_id, logger, self.session_id, turn_index)
