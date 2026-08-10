from __future__ import annotations

from aegis.integrations.calendar_client import CalendarApiError, list_all_events
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class ListEventsTool(Tool):
    name = "list_events"
    description = (
        "Google Calendar'daki etkinlikleri (son 90 gun - gelecek 365 gun araligi) listeler."
    )
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
            events = list_all_events()
        except (GoogleAuthError, CalendarApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        summary = ", ".join(f"{e['title']} ({e['when']})" for e in events) or "(bos)"
        return ToolResult(
            success=True,
            message=f"{len(events)} etkinlik: {summary}",
            data={"events": events},
        )
