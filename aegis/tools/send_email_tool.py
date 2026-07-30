"""Mock e-posta tool'u: gercek ag cagrisi YAPMAZ, sadece ne gonderilecegini
loglar. Gercek Microsoft Graph/IMAP entegrasyonu bilerek ileri faza birakildi."""

from __future__ import annotations

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class SendEmailTool(Tool):
    name = "send_email"
    description = "Belirtilen adrese e-posta gonderir (bu surumde MOCK - gercekten gondermez)."
    risk_level = RiskLevel.MEDIUM

    def build_schema(self, ctx: ToolContext) -> dict:
        email_enum = ctx.candidates.emails + [YOK]
        text_enum = ctx.candidates.quoted_spans + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "enum": email_enum, "description": "Alici adresi. Yoksa YOK."},
                    "subject": {"type": "string", "enum": text_enum, "description": "Konu. Yoksa YOK."},
                    "body": {"type": "string", "enum": text_enum, "description": "Govde. Yoksa YOK."},
                },
                "required": ["to", "subject", "body"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(slot_name="to", candidates=ctx.candidates.emails),
            SlotRequirement(slot_name="subject", candidates=ctx.candidates.quoted_spans),
            SlotRequirement(slot_name="body", candidates=ctx.candidates.quoted_spans),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        to = resolved_args.get("to")
        subject = resolved_args.get("subject")
        body = resolved_args.get("body")
        if not to or not subject or not body:
            return ToolResult(success=False, message="Eksik parametre (to/subject/body).")
        # Kasitli olarak ag cagrisi yok - sadece mock log.
        return ToolResult(
            success=True,
            message=f"[MOCK EMAIL] to={to} subject={subject!r} body={body!r} (gercekten gonderilmedi)",
            data={"to": to, "subject": subject, "body": body, "mock": True},
        )
