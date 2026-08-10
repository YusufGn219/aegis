"""E-posta gonderme tool'u: Gmail API'ye (yalnizca gmail.send scope) baglanir,
bkz. aegis.integrations.gmail_client. Bu dosya sadece "ne gonderilecek"le
ilgilenir - yetkilendirme/MIME/API detaylari gmail_client'ta izole edilmis."""

from __future__ import annotations

from aegis.integrations.gmail_client import GmailAuthError, GmailApiError, send_email
from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class SendEmailTool(Tool):
    name = "send_email"
    description = "Belirtilen adrese Gmail uzerinden e-posta gonderir."
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
                    "subject": {
                        "type": "string",
                        "enum": text_enum,
                        "description": "Konu (mesajdaki ILK tirnakli ifade). Yoksa YOK.",
                    },
                    "body": {
                        "type": "string",
                        "enum": text_enum,
                        "description": "Govde (mesajdaki IKINCI tirnakli ifade). Yoksa YOK.",
                    },
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
        try:
            message_id = send_email(to, subject, body)
        except (GmailAuthError, GmailApiError) as exc:
            return ToolResult(success=False, message=str(exc))
        return ToolResult(
            success=True,
            message=f"E-posta gonderildi: to={to} subject={subject!r} (id={message_id})",
            data={"to": to, "subject": subject, "body": body, "message_id": message_id},
        )
