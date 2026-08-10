from __future__ import annotations

from aegis.integrations.drive_client import DriveApiError, list_notes
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class ListNotesTool(Tool):
    name = "list_notes"
    description = "Google Drive'daki ('aegis Notlar' klasorunde) notlari listeler."
    risk_level = RiskLevel.LOW

    def build_schema(self, ctx: ToolContext) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": {}, "required": []},
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return []

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        try:
            notes = list_notes()
        except (GoogleAuthError, DriveApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        titles = [n["title"] for n in notes]
        return ToolResult(
            success=True,
            message=f"{len(notes)} not: {', '.join(titles) or '(bos)'}",
            data={"notes": notes},
        )
