from __future__ import annotations

import os

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class DeleteFileTool(Tool):
    name = "delete_file"
    description = "Bir dosyayi kalici olarak siler (GERI ALINAMAZ)."
    risk_level = RiskLevel.HIGH

    def build_schema(self, ctx: ToolContext) -> dict:
        filename_enum = ctx.candidates.filenames + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "enum": filename_enum,
                        "description": "Silinecek dosyanin kullanicinin yazdigi adi. Yoksa YOK.",
                    },
                },
                "required": ["target"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(
                slot_name="target", candidates=ctx.candidates.filenames, is_filesystem_path=True
            )
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        target_path = resolved_args.get("target")
        if not target_path:
            return ToolResult(success=False, message="Eksik parametre: target")

        sandbox_root = os.path.abspath(ctx.sandbox_root)
        abs_path = os.path.abspath(target_path)
        if os.path.commonpath([sandbox_root, abs_path]) != sandbox_root:
            return ToolResult(
                success=False,
                message=f"Guvenlik: target sandbox disinda ({target_path}), islem reddedildi.",
            )

        if not os.path.isfile(target_path):
            return ToolResult(success=False, message=f"Dosya bulunamadi: {target_path}")

        os.remove(target_path)
        return ToolResult(
            success=True,
            message=f"{target_path} silindi.",
            data={"deleted": target_path},
        )
