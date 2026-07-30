"""CLI giris noktasi. 'UI hicbir is yapmaz, sadece istegi iletir' ilkesini
kasitli olarak bu basit CLI ile karsiliyoruz - ileride FastAPI/PySide6 UI'lar
ayni ToolResult sozlesmesini kullanacak (POST /request {message} -> ToolResult)."""

from __future__ import annotations

import sys
import uuid

from aegis.coordinator.coordinator import Coordinator
from aegis.logging_.event_log import StructuredLogger


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
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
