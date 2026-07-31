"""CLI giris noktasi. 'UI hicbir is yapmaz, sadece istegi iletir' ilkesini
kasitli olarak bu basit CLI ile karsiliyoruz - ileride FastAPI/PySide6 UI'lar
ayni ToolResult sozlesmesini kullanacak (POST /request {message} -> ToolResult)."""

from __future__ import annotations

import sys
import uuid

from aegis.coordinator.coordinator import Coordinator
from aegis.logging_.event_log import LogEvent, StructuredLogger


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

    logger = StructuredLogger()
    request_id = str(uuid.uuid4())
    coordinator = Coordinator()
    result = coordinator.route(user_message, request_id, logger)

    print(result.message)
    _collect_feedback(logger, request_id)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
