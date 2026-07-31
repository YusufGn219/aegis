from __future__ import annotations

import os

from aegis.tools.add_event_tool import CALENDAR_FILENAME, _load_events
from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class ListEventsTool(Tool):
    name = "list_events"
    description = "Sandbox icindeki calendar.json dosyasindaki etkinlikleri listeler."
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
        summary = ", ".join(f"{e['title']} ({e['date']})" for e in events) or "(bos)"
        return ToolResult(
            success=True,
            message=f"{len(events)} etkinlik: {summary}",
            data={"events": events},
        )
