"""delete_event_tool ile ayni "once baslikla bul" desenini paylasir: 0 ya da
2+ eslesme (gercek belirsizlik) varsa GUNCELLEME YAPILMAZ. add_event/
delete_event'ten farkli olarak MEDIUM risk - yanlis olsa bile geri
alinabilir (tekrar guncellenebilir), delete gibi kalici degil."""

from __future__ import annotations

from aegis.integrations.calendar_client import CalendarApiError, find_events_by_title, update_event
from aegis.integrations.google_auth import GoogleAuthError
from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult


class UpdateEventTool(Tool):
    name = "update_event"
    description = "Basligina gore Google Calendar'daki bir etkinligin tarihini/saatini/tekrarini gunceller."
    risk_level = RiskLevel.MEDIUM

    def build_schema(self, ctx: ToolContext) -> dict:
        title_enum = ctx.candidates.quoted_spans + [YOK]
        date_enum = ctx.candidates.dates + [YOK]
        time_enum = ctx.candidates.times + [YOK]
        recurrence_enum = ctx.candidates.recurrences + [YOK]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "enum": title_enum,
                        "description": "Guncellenecek etkinligin basligi (tirnakli ifade). Yoksa YOK.",
                    },
                    "date": {
                        "type": "string",
                        "enum": date_enum,
                        "description": "Yeni tarih (GG.AA.YYYY). OPSIYONEL, degismiyorsa YOK.",
                    },
                    "time": {
                        "type": "string",
                        "enum": time_enum,
                        "description": "Yeni saat (SS:DD). OPSIYONEL, degismiyorsa YOK.",
                    },
                    "recurrence": {
                        "type": "string",
                        "enum": recurrence_enum,
                        "description": "Yeni tekrar sikligi (gunluk/haftalik/aylik). OPSIYONEL, yoksa YOK.",
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

    def optional_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        return [
            SlotRequirement(
                slot_name="date", candidates=ctx.candidates.dates, is_filesystem_path=False
            ),
            SlotRequirement(
                slot_name="time", candidates=ctx.candidates.times, is_filesystem_path=False
            ),
            SlotRequirement(
                slot_name="recurrence", candidates=ctx.candidates.recurrences, is_filesystem_path=False
            ),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        title = resolved_args.get("title")
        if not title:
            return ToolResult(success=False, message="Eksik parametre (title).")

        date = resolved_args.get("date")
        time = resolved_args.get("time")
        recurrence = resolved_args.get("recurrence")
        if not (date or time or recurrence):
            return ToolResult(
                success=False,
                message="Guncellenecek bir sey belirtilmedi (date/time/recurrence'tan en az biri gerekli).",
            )

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
            updated = update_event(match["id"], date, time, recurrence)
        except (GoogleAuthError, CalendarApiError) as exc:
            return ToolResult(success=False, message=str(exc))

        return ToolResult(
            success=True,
            message=f"Etkinlik guncellendi: {updated['title']} ({updated['when']}).",
            data={"updated": updated},
        )
