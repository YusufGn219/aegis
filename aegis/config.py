"""Aegis icin merkezi konfigurasyon. Ortam degiskenleriyle override edilebilir."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VLLM_BASE_URL = os.environ.get("AEGIS_VLLM_BASE_URL", "http://localhost:8000/v1")
MODEL_NAME = os.environ.get("AEGIS_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

SANDBOX_ROOT = Path(os.environ.get("AEGIS_SANDBOX_ROOT", str(PROJECT_ROOT / "workspace_sandbox")))
LOG_PATH = Path(os.environ.get("AEGIS_LOG_PATH", str(PROJECT_ROOT / "logs" / "events.jsonl")))

LLM_TIMEOUT_SECONDS = float(os.environ.get("AEGIS_LLM_TIMEOUT_SECONDS", "30"))

# Gmail API (gonderim - gmail.send scope) icin OAuth dosyalari. credentials.json
# Google Cloud Console'dan indirilen "Desktop app" OAuth client'i, token.json
# ilk basarili yetkilendirmeden sonra otomatik olusturulur/yenilenir.
GMAIL_CREDENTIALS_PATH = Path(
    os.environ.get("AEGIS_GMAIL_CREDENTIALS_PATH", str(PROJECT_ROOT / "credentials.json"))
)
GMAIL_TOKEN_PATH = Path(
    os.environ.get("AEGIS_GMAIL_TOKEN_PATH", str(PROJECT_ROOT / "token.json"))
)
