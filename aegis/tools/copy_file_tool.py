from __future__ import annotations

import os
import shutil

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class CopyFileTool(Tool):
    name = "copy_file"
    description = "Bir dosyayi baska bir klasore kopyalar (kaynak yerinde kalir)."
    risk_level = RiskLevel.MEDIUM

    def build_schema(self, ctx: ToolContext) -> dict:
        filename_enum = ctx.candidates.filenames + [YOK]
        folder_enum = ctx.candidates.folder_names + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": filename_enum,
                        "description": "Kopyalanacak dosyanin kullanicinin yazdigi adi. Yoksa YOK.",
                    },
                    "destination": {
                        "type": "string",
                        "enum": folder_enum,
                        "description": "Hedef klasorun kullanicinin yazdigi adi. Yoksa YOK.",
                    },
                },
                "required": ["source", "destination"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(
                slot_name="source", candidates=ctx.candidates.filenames, is_filesystem_path=True
            ),
            SlotRequirement(
                slot_name="destination",
                candidates=ctx.candidates.folder_names,
                is_filesystem_path=True,
            ),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        source_path = resolved_args.get("source")
        destination_path = resolved_args.get("destination")
        sandbox_root = os.path.abspath(ctx.sandbox_root)

        for label, path in (("source", source_path), ("destination", destination_path)):
            if not path:
                return ToolResult(success=False, message=f"Eksik parametre: {label}")
            abs_path = os.path.abspath(path)
            if os.path.commonpath([sandbox_root, abs_path]) != sandbox_root:
                return ToolResult(
                    success=False,
                    message=f"Guvenlik: {label} sandbox disinda ({path}), islem reddedildi.",
                )

        if not os.path.isfile(source_path):
            return ToolResult(success=False, message=f"Kaynak dosya bulunamadi: {source_path}")
        if not os.path.isdir(destination_path):
            return ToolResult(success=False, message=f"Hedef klasor bulunamadi: {destination_path}")

        target_path = os.path.join(destination_path, os.path.basename(source_path))
        shutil.copy2(source_path, target_path)
        return ToolResult(
            success=True,
            message=f"{source_path} -> {target_path} kopyalandi.",
            data={"from": source_path, "to": target_path},
        )
