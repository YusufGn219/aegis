#!/usr/bin/env python3
"""Izole test sandbox'ini sifirlayip sahte dosya/klasorlerle doldurur.
Sadece workspace_sandbox/ icinde calisir - gercek Masaustu/Indirilenler'e
ASLA dokunmaz. Idempotent: her calistirmada onceki icerigi silip yeniden
kurar."""

from __future__ import annotations

import shutil

from aegis import config

# Tek dogruluk kaynagi aegis.config.SANDBOX_ROOT - bu script'in dosya sistemindeki
# konumundan bagimsiz, her zaman uygulamanin da kullandigi ayni sandbox'i hedefler.
SANDBOX_ROOT = config.SANDBOX_ROOT

SEED_FOLDERS = ["Downloads", "Arşiv", "Belgeler"]
SEED_FILES = {
    "Downloads/rapor.pdf": "dummy pdf content",
    "Downloads/fatura_2026.xlsx": "dummy xlsx content",
    "Downloads/tatil_fotograf.jpg": "dummy jpg content",
}


def seed() -> None:
    for folder in SEED_FOLDERS:
        path = SANDBOX_ROOT / folder
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)

    for rel_path, content in SEED_FILES.items():
        full_path = SANDBOX_ROOT / rel_path
        full_path.write_text(content, encoding="utf-8")

    print(f"Sandbox sifirlandi: {SANDBOX_ROOT}")
    for folder in SEED_FOLDERS:
        entries = sorted(p.name for p in (SANDBOX_ROOT / folder).iterdir())
        print(f"  {folder}/: {entries}")


if __name__ == "__main__":
    seed()
