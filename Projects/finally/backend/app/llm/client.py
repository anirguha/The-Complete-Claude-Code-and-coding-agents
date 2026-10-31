"""The one real LLM call: LiteLLM to OpenRouter, with Cerebras as the provider.

litellm is imported on the first call, not at module load. It takes seconds to
import, and app startup and non-chat use should not pay for that.
"""

import asyncio
import importlib
import os
from typing import Any

from .schema import AssistantReply

# Without this, importing litellm fetches a price map from GitHub.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
TIMEOUT_SECONDS = 30.0


def _load_litellm() -> Any:
    litellm = importlib.import_module("litellm")
    litellm.suppress_debug_info = True  # otherwise failures print banners to stdout
    return litellm


async def _complete(messages: list[dict[str, str]], api_key: str) -> Any:
    litellm = await asyncio.to_thread(_load_litellm)
    response = await litellm.acompletion(
        model=MODEL,
        messages=messages,
        response_format=AssistantReply,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
        api_key=api_key,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,  # retries would multiply the time the user waits
    )
    return response.choices[0].message.content


async def request_completion(messages: list[dict[str, str]], api_key: str) -> Any:
    """Return the reply's raw content. Raises on any failure, including the 30s limit.

    `timeout` above bounds each network wait; wait_for bounds the call as a whole.
    """
    return await asyncio.wait_for(_complete(messages, api_key), TIMEOUT_SECONDS)
