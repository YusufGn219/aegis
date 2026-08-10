"""Etkinlik baslikla silinir (kullanici Google'in event id'sini bilemez);
delete_file_tool'dan sonra HIGH risk tier'i kullanan ikinci tool.
Once find_events_by_title ile GERCEK adaylar bulunur - 0 eslesme ya da 2+
eslesme (gercek belirsizlik) durumunda SILME YAPILMAZ, kullaniciya daha
spesifik yazmasi soylenir (path_resolver'in AMBIGUOUS/NOT_FOUND felsefesiyle
ayni: asla tahmin etme)."""

from __future__ import annotations

from aegis.integrations.calendar_client import CalendarApiError, delete_event, find_events_by_title
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class DeleteEventTool(Tool):
    name = "delete_event"
    description = "Basligina gore Google Calendar'dan bir etkinligi kalici olarak siler (GERI ALINAMAZ)."
    risk_level = RiskLevel.HIGH

    def build_schema(self, ctx: ToolContext) -> dict:
        title_enum = ctx.candidates.quoted_spans + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "enum": title_enum,
                        "description": "Silinecek etkinligin basligi (mesajdaki tirnakli ifade). Yoksa YOK.",
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

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        title = resolved_args.get("title")
        if not title:
            return ToolResult(success=False, message="Eksik parametre (title).")

        try:
            matches = find_events_by_title(title)
        except (GoogleAuthError, CalendarApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        if not matches:
            return ToolResult(
                success=False, message=f"'{title}' basligiyla eslesen bir etkinlik bulunamadi."
            )

        if len(matches) > 1:
            candidates = "; ".join(f"{m['title']} ({m['when']})" for m in matches)
            return ToolResult(
                success=False,
                message=(
                    f"'{title}' icin birden fazla etkinlik bulundu, hangisi oldugu belirsiz: "
                    f"{candidates}. Lutfen tarihini de belirterek tekrar deneyin."
                ),
            )

        match = matches[0]
        try:
            delete_event(match["id"])
        except (GoogleAuthError, CalendarApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        return ToolResult(
            success=True,
            message=f"Etkinlik silindi: {match['title']} ({match['when']}).",
            data={"deleted": match},
        )
