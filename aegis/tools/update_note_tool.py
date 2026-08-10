"""delete_note_tool ile ayni "once baslikla bul" desenini paylasir. Sadece
IcERIK guncellenir - yeniden adlandirma desteklenmiyor (baslik hem "hangi
notu bul" hem "yeni baslik" olarak kullanilsaydi create_note/update_note
arasindaki mevcut LLM-verb ayrimini karistirirdi, bkz. update_event_tool'daki
ayni tasarim notu)."""

from __future__ import annotations

from aegis.integrations.drive_client import DriveApiError, find_notes_by_title, update_note
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class UpdateNoteTool(Tool):
    name = "update_note"
    description = "Basligina gore Google Drive'daki bir notun icerigini gunceller."
    risk_level = RiskLevel.MEDIUM

    def build_schema(self, ctx: ToolContext) -> dict:
        text_enum = ctx.candidates.quoted_spans + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "enum": text_enum,
                        "description": "Guncellenecek notun basligi (tirnakli ifade). Yoksa YOK.",
                    },
                    "content": {
                        "type": "string",
                        "enum": text_enum,
                        "description": "Notun yeni icerigi. OPSIYONEL, degismiyorsa YOK.",
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

    def optional_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(
                slot_name="content", candidates=ctx.candidates.quoted_spans, is_filesystem_path=False
            ),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        title = resolved_args.get("title")
        if not title:
            return ToolResult(success=False, message="Eksik parametre (title).")

        content = resolved_args.get("content")
        if not content:
            return ToolResult(success=False, message="Guncellenecek yeni icerik belirtilmedi.")

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
                    "oldugu belirsiz. Guncelleme iptal edildi."
                ),
            )

        match = matches[0]
        try:
            updated = update_note(match["id"], content)
        except (GoogleAuthError, DriveApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        return ToolResult(
            success=True,
            message=f"Not guncellendi: {updated['title']}.",
            data={"updated": updated},
        )
