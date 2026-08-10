"""Dosya-sistemi islemleri Skill'i - ince sarmalayici, asil orkestrasyon
tool_selection_engine.run_tool_selection()'da (NotesSkill/CalendarSkill ile
paylasilan ortak motor)."""

from __future__ import annotations

from aegis.logging_.event_log import StructuredLogger
from aegis.permission.engine import PermissionEngine
from aegis.skills.base import Skill
from aegis.skills.tool_selection_engine import run_tool_selection
from aegis.tools.base import Tool, ToolResult
from aegis.tools.copy_file_tool import CopyFileTool
from aegis.tools.create_folder_tool import CreateFolderTool
from aegis.tools.delete_file_tool import DeleteFileTool
from aegis.tools.list_files_tool import ListFilesTool
from aegis.tools.list_inbox_emails_tool import ListInboxEmailsTool
from aegis.tools.move_file_tool import MoveFileTool
from aegis.tools.send_email_tool import SendEmailTool


class WorkspaceOrganizerSkill(Skill):
    name = "workspace_organizer"

    def __init__(self):
        self.tools: list[Tool] = [
            ListFilesTool(),
            MoveFileTool(),
            SendEmailTool(),
            ListInboxEmailsTool(),
            CopyFileTool(),
            DeleteFileTool(),
            CreateFolderTool(),
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
