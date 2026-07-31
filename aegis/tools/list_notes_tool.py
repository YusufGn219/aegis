from __future__ import annotations

import os

from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class ListNotesTool(Tool):
    name = "list_notes"
    description = "Sandbox icindeki Notlar klasorundeki notlari listeler."
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
        notes_dir = os.path.join(ctx.sandbox_root, "Notlar")
        if not os.path.isdir(notes_dir):
            return ToolResult(success=True, message="Notlar klasoru bos (henuz not yok).", data={"notes": []})

        notes = sorted(os.listdir(notes_dir))
        return ToolResult(
            success=True,
            message=f"{len(notes)} not: {', '.join(notes) or '(bos)'}",
            data={"notes": notes},
        )
