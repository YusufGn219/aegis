"""Su an tek bir Agent kayitli oldugu icin bu sinif kasitli olarak trivial.
Var olma amaci, arayuzu ('mesaj -> ToolResult') simdiden sabitlemek: ileride
coklu-Agent yonlendirmesi (orn. workspace vs mail vs takvim) eklendiginde,
CLI hic degismeyecek - sadece route()'un ic mantigi genisleyecek (kucuk bir
deterministik anahtar-kelime kontrolu ya da LLM tabanli bir yonlendirme)."""

from __future__ import annotations

import uuid

from aegis.agents.base import Agent
from aegis.agents.workspace_agent import WorkspaceAgent
from aegis.logging_.event_log import LogEvent, StructuredLogger
from aegis.tools.base import ToolResult


class Coordinator:
    def __init__(self):
        self.agents: dict[str, Agent] = {"workspace_agent": WorkspaceAgent()}
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
        agent = self.agents["workspace_agent"]
        return agent.handle(user_message, request_id, logger, self.session_id, turn_index)
