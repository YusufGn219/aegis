"""Risk seviyesine gore izin kapisi. LOW otomatik gecer; MEDIUM/HIGH,
kullaniciya GERCEK (cozumlenmis) degerleri gosterip CLI'da onay ister.
HIGH tier bu dilimde hicbir tool tarafindan kullanilmiyor ama gate kodu
(delete/registry/format gibi ileri faz tool'lari icin) burada hazir."""

from __future__ import annotations

from aegis.tools.base import RiskLevel, Tool


class PermissionEngine:
    def check_and_confirm(self, tool: Tool, resolved_args: dict) -> bool:
        if tool.risk_level == RiskLevel.LOW:
            return True

        print(f"\n[ONAY GEREKLI - {tool.risk_level.value}] {tool.name}")
        for key, value in resolved_args.items():
            print(f"    {key} = {value}")
        if tool.risk_level == RiskLevel.HIGH:
            print("    !!! BU ISLEM GERI ALINAMAZ OLABILIR !!!")
        answer = input("Devam edilsin mi? [y/N]: ").strip().lower()
        return answer == "y"
