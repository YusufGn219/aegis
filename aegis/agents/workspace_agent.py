"""Su an tek bir Skill'e sahip oldugu icin bu Agent kasitli olarak
pass-through (dogrudan devreder). handle()'in imzasi ('mesaj -> skill sec ->
devret') ileride birden fazla Skill eklendiginde Coordinator'i ya da CLI'i
hic degistirmeden, sadece bu metodun ic mantigini genisleterek yonlendirme
yapabilecek sekilde yazildi."""

from __future__ import annotations

from aegis.agents.base import Agent
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.workspace_organizer_skill import WorkspaceOrganizerSkill
from aegis.tools.base import ToolResult


class WorkspaceAgent(Agent):
    name = "workspace_agent"

    def __init__(self):
        self.skills = [WorkspaceOrganizerSkill()]

    def handle(self, user_message: str, request_id: str, logger: StructuredLogger) -> ToolResult:
        # Tek Skill oldugu icin secim trivial; ileride birden fazla Skill
        # olunca burada (invocation_policy'ye benzer sekilde) deterministik-
        # once, LLM-gerekirse yaklasimi uygulanacak.
        skill = self.skills[0]
        return skill.run(user_message, request_id, logger)
