from __future__ import annotations

from aegis.integrations.calendar_client import CalendarApiError, list_upcoming_events
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


def _describe(event: dict) -> str:
    text = f"{event['title']} ({event['when']})"
    if event.get("recurring"):
        text += " [tekrarli]"
    return text


class ListUpcomingEventsTool(Tool):
    name = "list_upcoming_events"
    description = "Su andan itibaren Google Calendar'daki yaklasan etkinlikleri listeler."
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
            events = list_upcoming_events()
        except (GoogleAuthError, CalendarApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        summary = ", ".join(_describe(e) for e in events) or "(yaklasan etkinlik yok)"
        return ToolResult(
            success=True,
            message=f"{len(events)} yaklasan etkinlik: {summary}",
            data={"events": events},
        )
