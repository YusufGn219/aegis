from __future__ import annotations

import json
import os

from aegis.tools.base import YOK, RiskLevel, SlotRequirement, Tool, ToolContext, ToolResult

CALENDAR_FILENAME = "calendar.json"


def _load_events(calendar_path: str) -> list[dict]:
    if not os.path.isfile(calendar_path):
        return []
    with open(calendar_path, encoding="utf-8") as f:
        return json.load(f)


class AddEventTool(Tool):
    name = "add_event"
    description = "Sandbox icindeki calendar.json dosyasina yeni bir etkinlik ekler."
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
                        "description": "Etkinlik basligi (mesajdaki tirnakli ifade). Yoksa YOK.",
                    },
                    "date": {
                        "type": "string",
                        "enum": date_enum,
                        "description": "Etkinlik tarihi (GG.AA.YYYY, mesajda gectigi hali). Yoksa YOK.",
                    },
                    "time": {
                        "type": "string",
                        "enum": time_enum,
                        "description": "Etkinlik saati (SS:DD, mesajda gectigi hali). OPSIYONEL, yoksa YOK.",
                    },
                    "recurrence": {
                        "type": "string",
                        "enum": recurrence_enum,
                        "description": (
                            "Tekrar sikligi (gunluk/haftalik/aylik). OPSIYONEL, yoksa YOK."
                        ),
                    },
                },
                # time/recurrence bilerek "required" listesinde DEGIL -
                # invocation_policy'nin skip_llm kurali bu yuzden hala
                # sadece title+date'e bakiyor (bkz. required_slots()).
                "required": ["title", "date"],
            },
        }

    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        # BILINEN SINIRLAMA: time/recurrence burada YOK - invocation_policy
        # skip_llm kararini SADECE bu listeye bakarak veriyor. Yani title+date
        # tam 1'er aday oldugunda (cok sik rastlanan durum) akis LLM'e hic
        # gitmeden otomatik cozuluyor VE bu durumda mesajda gecen time/
        # recurrence bilgisi - ne kadar acik yazilmis olursa olsun -
        # SESSIZCE KAYBOLUYOR (auto_resolved sadece required slotlari
        # dolduruyor). Duzeltilmedi: invocation_policy'yi "opsiyonel ama
        # tek adayli slotlar" kavramina genisletmek bu oturumun kapsami
        # disinda tutuldu (bkz. vault notu).
        return [
            SlotRequirement(
                slot_name="title", candidates=ctx.candidates.quoted_spans, is_filesystem_path=False
            ),
            SlotRequirement(
                slot_name="date", candidates=ctx.candidates.dates, is_filesystem_path=False
            ),
        ]

    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        title = resolved_args.get("title")
        date = resolved_args.get("date")
        if not title or not date:
            return ToolResult(success=False, message="Eksik parametre (title/date).")

        time = resolved_args.get("time")
        recurrence = resolved_args.get("recurrence")

        calendar_path = os.path.join(ctx.sandbox_root, CALENDAR_FILENAME)
        events = _load_events(calendar_path)
        events.append({"title": title, "date": date, "time": time, "recurrence": recurrence})
        with open(calendar_path, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

        extra = ""
        if time:
            extra += f" {time}"
        if recurrence:
            extra += f" ({recurrence} tekrar)"
        return ToolResult(
            success=True,
            message=f"Etkinlik eklendi: {title} ({date}{extra}).",
            data={"title": title, "date": date, "time": time, "recurrence": recurrence},
        )
