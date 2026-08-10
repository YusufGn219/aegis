"""CLI giris noktasi. 'UI hicbir is yapmaz, sadece istegi iletir' ilkesini
kasitli olarak bu basit CLI ile karsiliyoruz - ileride FastAPI/PySide6 UI'lar
ayni ToolResult sozlesmesini kullanacak (POST /request {message} -> ToolResult)."""

from __future__ import annotations

import sys
import uuid

from aegis.coordinator.coordinator import Coordinator
from aegis.logging_.event_log import LogEvent, StructuredLogger

CAPABILITY_COMMANDS = {"/yetenekler", "/islevler", "/işlevler", "/help", "/yardim"}


def _print_capabilities(coordinator: Coordinator) -> None:
    """Kayitli Agent/Skill/Tool'lardan otomatik uretilen bir ozet - elle
    guncel tutulmasi gereken ayri bir liste degil, tool eklendikce/
    kaldirildikca burasi da otomatik dogru kalir."""
    print("aegis su an dogal dille sunlari yapabilir:\n")
    for agent in coordinator.agents.values():
        for skill in agent.skills:
            print(f"[{skill.name}]")
            for tool in skill.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()
    print(
        "Bir istegi dogal dille yazman yeterli, orn.:\n"
        '  python -m aegis "Downloads klasorundeki dosyalari listele"\n'
        '  python -m aegis "ahmet@example.com adresine \'Konu\' konulu \'Govde\' icerikli mail gonder"'
    )


def _collect_feedback(logger: StructuredLogger, request_id: str) -> None:
    """Fine-tuning veri setinde ornekleri etiketlemek icin: kullaniciya
    sonucun dogru olup olmadigini sorar, opsiyoneldir (bos/'skip' gecilebilir)."""
    try:
        answer = input("Bu dogru muydu? (e/h/skip): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if answer not in ("e", "h"):
        return
    logger.log(
        LogEvent(
            request_id=request_id,
            step="feedback",
            decision="kullanici geri bildirimi",
            success=True,
            user_feedback="dogru" if answer == "e" else "yanlis",
        )
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    user_message = " ".join(sys.argv[1:])
    if not user_message:
        print('Kullanim: python -m aegis "<istek>"')
        sys.exit(1)

    coordinator = Coordinator()

    if user_message.strip().casefold() in CAPABILITY_COMMANDS:
        _print_capabilities(coordinator)
        sys.exit(0)

    logger = StructuredLogger()
    request_id = str(uuid.uuid4())
    result = coordinator.route(user_message, request_id, logger)

    print(result.message)
    _collect_feedback(logger, request_id)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
