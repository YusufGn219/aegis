"""Gelen kutusunu ozetleyen salt-okunur tool. Slotsuz - list_upcoming_events_tool
ile ayni pattern (kullanicinin belirtecegi bir deger yok, LLM'e hic sormadan
calisir)."""

from __future__ import annotations

from aegis.integrations.gmail_client import GmailApiError, GmailAuthError, list_recent_emails
from aegis.tools.base import RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult

MAX_RESULTS = 5


class ListInboxEmailsTool(Tool):
    name = "list_inbox_emails"
    description = "Gelen kutusundaki en son mailleri (gonderen/konu/tarih/ozet) listeler."
    risk_level = RiskLevel.LOW

    def build_schema(self, ctx: ToolContext) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": {}, "required": []},
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return []

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        try:
            emails = list_recent_emails(max_results=MAX_RESULTS)
        except (GmailAuthError, GmailApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        if not emails:
            return ToolResult(success=True, message="Gelen kutusu bos.", data={"emails": []})

        summary = "; ".join(f"{e['from']} - {e['subject']!r}" for e in emails)
        return ToolResult(
            success=True,
            message=f"{len(emails)} mail: {summary}",
            data={"emails": emails},
        )
