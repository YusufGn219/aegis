"""Etkinlik ekleme/listeleme Skill'i - ince sarmalayici, asil orkestrasyon
tool_selection_engine.run_tool_selection()'da (WorkspaceOrganizerSkill ile
paylasilan ortak motor)."""

from __future__ import annotations

from aegis.logging_.event_log import StructuredLogger
from aegis.permission.engine import PermissionEngine
from aegis.skills.base import Skill
from aegis.skills.tool_selection_engine import run_tool_selection
from aegis.tools.add_event_tool import AddEventTool
from aegis.tools.base import Tool, ToolResult
from aegis.tools.list_events_tool import ListEventsTool
from aegis.tools.list_upcoming_events_tool import ListUpcomingEventsTool


class CalendarSkill(Skill):
    name = "calendar"

    def __init__(self):
        self.tools: list[Tool] = [AddEventTool(), ListEventsTool(), ListUpcomingEventsTool()]
        self.permission_engine = PermissionEngine()

    def run(
        self,
        user_message: str,
        request_id: str,
        logger: StructuredLogger,
        session_id: str | None = None,
        turn_index: int | None = None,
    ) -> ToolResult:
        return run_tool_selection(
            user_message,
            request_id,
            logger,
            self.tools,
            self.name,
            self.permission_engine,
            session_id,
            turn_index,
        )
