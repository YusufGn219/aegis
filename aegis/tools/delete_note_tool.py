"""delete_event_tool ile ayni "once baslikla bul" desenini paylasir: 0 ya da
2+ eslesme (gercek belirsizlik) varsa SILME YAPILMAZ."""

from __future__ import annotations

from aegis.integrations.drive_client import DriveApiError, delete_note, find_notes_by_title
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class DeleteNoteTool(Tool):
    name = "delete_note"
    description = "Basligina gore Google Drive'daki bir notu kalici olarak siler (GERI ALINAMAZ)."
    risk_level = RiskLevel.HIGH

    def build_schema(self, ctx: ToolContext) -> dict:
        title_enum = ctx.candidates.quoted_spans + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "enum": title_enum,
                        "description": "Silinecek notun basligi (tirnakli ifade). Yoksa YOK.",
                    },
                },
                "required": ["title"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(
                slot_name="title", candidates=ctx.candidates.quoted_spans, is_filesystem_path=False
            ),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        title = resolved_args.get("title")
        if not title:
            return ToolResult(success=False, message="Eksik parametre (title).")

        try:
            matches = find_notes_by_title(title)
        except (GoogleAuthError, DriveApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        if not matches:
            return ToolResult(success=False, message=f"'{title}' basligiyla eslesen bir not bulunamadi.")

        if len(matches) > 1:
            return ToolResult(
                success=False,
                message=(
                    f"'{title}' icin birden fazla not bulundu ({len(matches)} adet), hangisi "
                    "oldugu belirsiz. Silme islemi iptal edildi."
                ),
            )

        match = matches[0]
        try:
            delete_note(match["id"])
        except (GoogleAuthError, DriveApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        return ToolResult(
            success=True,
            message=f"Not silindi: {match['title']}.",
            data={"deleted": match},
        )
