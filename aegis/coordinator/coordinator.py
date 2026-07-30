"""Su an tek bir Agent kayitli oldugu icin bu sinif kasitli olarak trivial.
Var olma amaci, arayuzu ('mesaj -> ToolResult') simdiden sabitlemek: ileride
coklu-Agent yonlendirmesi (orn. workspace vs mail vs takvim) eklendiginde,
CLI hic degismeyecek - sadece route()'un ic mantigi genisleyecek (kucuk bir
deterministik anahtar-kelime kontrolu ya da LLM tabanli bir yonlendirme)."""

from __future__ import annotations

from aegis.agents.base import Agent
from aegis.agents.workspace_agent import WorkspaceAgent
from aegis.logging_.event_log import StructuredLogger
from aegis.tools.base import ToolResult


class Coordinator:
    def __init__(self):
        self.agents: dict[str, Agent] = {"workspace_agent": WorkspaceAgent()}

    def route(self, user_message: str, request_id: str, logger: StructuredLogger) -> ToolResult:
        agent = self.agents["workspace_agent"]
        return agent.handle(user_message, request_id, logger)
