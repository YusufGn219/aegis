"""vLLM'in OpenAI-uyumlu API'sine ince bir sarmalayici."""

from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletion

from aegis import config

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=config.VLLM_BASE_URL,
            api_key="not-needed",
            timeout=config.LLM_TIMEOUT_SECONDS,
            max_retries=1,
        )
    return _client


def call_for_tool_selection(request: dict) -> ChatCompletion:
    """request, prompt_builder.assemble_request() ciktisidir (model/messages/
    tools/tool_choice/temperature icerir)."""
    client = get_client()
    return client.chat.completions.create(**request)
