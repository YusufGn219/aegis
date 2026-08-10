"""Not olusturma/listeleme Skill'i - ince sarmalayici, asil orkestrasyon
tool_selection_engine.run_tool_selection()'da (WorkspaceOrganizerSkill ile
paylasilan ortak motor)."""

from __future__ import annotations

from aegis.logging_.event_log import StructuredLogger
from aegis.permission.engine import PermissionEngine
from aegis.skills.base import Skill
from aegis.skills.tool_selection_engine import run_tool_selection
from aegis.tools.base import Tool, ToolResult
from aegis.tools.create_note_tool import CreateNoteTool
from aegis.tools.delete_note_tool import DeleteNoteTool
from aegis.tools.list_notes_tool import ListNotesTool
from aegis.tools.update_note_tool import UpdateNoteTool


class NotesSkill(Skill):
    name = "notes"

    def __init__(self):
        self.tools: list[Tool] = [
            CreateNoteTool(),
            ListNotesTool(),
            DeleteNoteTool(),
            UpdateNoteTool(),
        ]
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
