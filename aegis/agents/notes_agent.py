"""Su an tek bir Skill'e sahip oldugu icin bu Agent kasitli olarak
pass-through (bkz. WorkspaceAgent)."""

from __future__ import annotations

from aegis.agents.base import Agent
from aegis.logging_.event_log import StructuredLogger
from aegis.skills.notes_skill import NotesSkill
from aegis.tools.base import ToolResult


class NotesAgent(Agent):
    name = "notes_agent"

    def __init__(self):
        self.skills = [NotesSkill()]

    def handle(
        self,
        user_message: str,
        request_id: str,
        logger: StructuredLogger,
        session_id: str | None = None,
        turn_index: int | None = None,
    ) -> ToolResult:
        skill = self.skills[0]
        return skill.run(user_message, request_id, logger, session_id, turn_index)
