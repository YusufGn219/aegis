from __future__ import annotations

import os
from datetime import date, datetime

from aegis.tools.add_event_tool import CALENDAR_FILENAME, _load_events
from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


def _parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None


class ListUpcomingEventsTool(Tool):
    name = "list_upcoming_events"
    description = "Bugunden itibaren yaklasan etkinlikleri (hatirlatma amacli) listeler."
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
        calendar_path = os.path.join(ctx.sandbox_root, CALENDAR_FILENAME)
        events = _load_events(calendar_path)

        today = date.today()
        upcoming = []
        for event in events:
            parsed = _parse_date(event.get("date", ""))
            if parsed is not None and parsed >= today:
                upcoming.append((parsed, event))
        upcoming.sort(key=lambda item: item[0])

        def _describe(event: dict) -> str:
            text = f"{event['title']} ({event['date']}"
            if event.get("time"):
                text += f" {event['time']}"
            text += ")"
            if event.get("recurrence"):
                text += f" [{event['recurrence']} tekrar]"
            return text

        summary = ", ".join(_describe(e) for _, e in upcoming) or "(yaklasan etkinlik yok)"
        return ToolResult(
            success=True,
            message=f"{len(upcoming)} yaklasan etkinlik: {summary}",
            data={"events": [e for _, e in upcoming]},
        )
