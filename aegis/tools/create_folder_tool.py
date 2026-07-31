from __future__ import annotations

import os

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class CreateFolderTool(Tool):
    name = "create_folder"
    description = "Sandbox kokunde yeni bir klasor olusturur."
    risk_level = RiskLevel.MEDIUM

    def build_schema(self, ctx: ToolContext) -> dict:
        folder_enum = ctx.candidates.folder_names + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "enum": folder_enum,
                        "description": "Olusturulacak klasorun kullanicinin yazdigi adi. Yoksa YOK.",
                    },
                },
                "required": ["folder_name"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        # is_filesystem_path=False: bu, henuz VAR OLMAYAN yeni bir isim -
        # PathResolver sadece MEVCUT dosya/klasorleri cozer, bu yuzden burada
        # devreye girmemeli; raw aday (zaten enum-kisitli) dogrudan kullanilir.
        return [
            SlotRequirement(
                slot_name="folder_name",
                candidates=ctx.candidates.folder_names,
                is_filesystem_path=False,
            )
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        folder_name = resolved_args.get("folder_name")
        if not folder_name:
            return ToolResult(success=False, message="Eksik parametre: folder_name")

        sandbox_root = os.path.abspath(ctx.sandbox_root)
        target_path = os.path.abspath(os.path.join(sandbox_root, folder_name))
        if os.path.commonpath([sandbox_root, target_path]) != sandbox_root:
            return ToolResult(
                success=False,
                message=f"Guvenlik: hedef sandbox disinda ({folder_name}), islem reddedildi.",
            )

        if os.path.exists(target_path):
            return ToolResult(success=False, message=f"Klasor zaten var: {target_path}")

        os.makedirs(target_path)
        return ToolResult(
            success=True,
            message=f"{target_path} olusturuldu.",
            data={"created": target_path},
        )
