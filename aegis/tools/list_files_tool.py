from __future__ import annotations

import os

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class ListFilesTool(Tool):
    name = "list_files"
    description = "Bir klasordeki dosya ve alt klasorleri listeler."
    risk_level = RiskLevel.LOW

    def build_schema(self, ctx: ToolContext) -> dict:
        folder_enum = ctx.candidates.folder_names + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "enum": folder_enum,
                        "description": (
                            "Listelenecek klasorun kullanicinin mesajinda gectigi hali. "
                            "Uygun bir klasor adi yoksa YOK sec (sandbox kokunu listeler)."
                        ),
                    }
                },
                "required": ["folder"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(
                slot_name="folder",
                candidates=ctx.candidates.folder_names,
                is_filesystem_path=True,
            )
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        folder_path = resolved_args.get("folder") or ctx.sandbox_root
        if not os.path.isdir(folder_path):
            return ToolResult(success=False, message=f"Klasor bulunamadi: {folder_path}")
        entries = sorted(os.listdir(folder_path))
        return ToolResult(
            success=True,
            message=f"{folder_path} icindeki {len(entries)} oge: {', '.join(entries) or '(bos)'}",
            data={"folder": folder_path, "entries": entries},
        )
