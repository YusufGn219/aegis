from __future__ import annotations

from aegis.integrations.drive_client import DriveApiError, create_note
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class CreateNoteTool(Tool):
    name = "create_note"
    description = "Google Drive'da ('aegis Notlar' klasorunde) yeni bir not (metin dosyasi) olusturur."
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
                        "description": "Not basligi (mesajdaki ILK tirnakli ifade). Yoksa YOK.",
                    },
                    "content": {
                        "type": "string",
                        "enum": text_enum,
                        "description": "Not icerigi (mesajdaki IKINCI tirnakli ifade). Yoksa YOK.",
                    },
                },
                "required": ["title", "content"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        # is_filesystem_path=False: baslik/icerik PathResolver'in cozdugu
        # bir dosya sistemi yolu degil, dogrudan kullanilan metin.
        return [
            SlotRequirement(
                slot_name="title", candidates=ctx.candidates.quoted_spans, is_filesystem_path=False
            ),
            SlotRequirement(
                slot_name="content", candidates=ctx.candidates.quoted_spans, is_filesystem_path=False
            ),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        title = resolved_args.get("title")
        content = resolved_args.get("content")
        if not title or not content:
            return ToolResult(success=False, message="Eksik parametre (title/content).")

        try:
            file_id = create_note(title, content)
        except (GoogleAuthError, DriveApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        return ToolResult(
            success=True,
            message=f"Not olusturuldu: {title}",
            data={"title": title, "file_id": file_id},
        )
