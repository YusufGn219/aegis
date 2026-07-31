from __future__ import annotations

import os
import re

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult

_SLUG_RE = re.compile(r"[^\w\-]+")


def _slugify(title: str) -> str:
    slug = _SLUG_RE.sub("_", title).strip("_")
    return slug or "not"


class CreateNoteTool(Tool):
    name = "create_note"
    description = "Sandbox icindeki Notlar klasorune yeni bir not (metin dosyasi) olusturur."
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

        notes_dir = os.path.join(ctx.sandbox_root, "Notlar")
        os.makedirs(notes_dir, exist_ok=True)
        note_path = os.path.join(notes_dir, f"{_slugify(title)}.txt")
        if os.path.exists(note_path):
            return ToolResult(success=False, message=f"Not zaten var: {note_path}")

        with open(note_path, "w", encoding="utf-8") as f:
            f.write(f"{title}\n\n{content}\n")

        return ToolResult(
            success=True,
            message=f"{note_path} olusturuldu.",
            data={"path": note_path, "title": title},
        )
