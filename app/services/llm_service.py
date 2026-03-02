"""Kimi Coding LLM client – Anthropic-compatible API.

Kimi Coding (family/coding plan) uses the Anthropic messages API format.
Base URL: https://api.kimi.com/coding/
Model:    k2p5  (262k context, 32k max output – same model for short and long)
"""

import asyncio
import logging
from typing import Optional

from anthropic import AsyncAnthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Respect Kimi rate limits: max 3 concurrent requests
_semaphore = asyncio.Semaphore(3)

_client: Optional[AsyncAnthropic] = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(
            api_key=settings.KIMI_API_KEY,
            base_url=settings.KIMI_BASE_URL,
        )
    return _client


def _split_messages(
    messages: list[dict[str, str]],
) -> tuple[Optional[str], list[dict[str, str]]]:
    """Extract leading system message for the Anthropic API's `system` parameter."""
    if messages and messages[0]["role"] == "system":
        return messages[0]["content"], messages[1:]
    return None, messages


async def chat_complete(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,  # kept for API compat; unused by Anthropic
    retries: int = 3,
) -> tuple[str, int, int]:
    """
    Call Kimi Coding API with rate limiting and retry.

    Returns:
        (content, prompt_tokens, completion_tokens)
    """
    if model is None:
        model = settings.KIMI_MODEL_SHORT

    system, user_messages = _split_messages(messages)

    kwargs = {
        "model": model,
        "messages": user_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system

    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            async with _semaphore:
                response = await get_client().messages.create(**kwargs)
            content = response.content[0].text if response.content else ""
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0
            return content, input_tokens, output_tokens
        except Exception as exc:
            logger.warning("Kimi API error (attempt %d): %s", attempt + 1, exc)
            last_exc = exc
            if attempt < retries - 1:
                await asyncio.sleep(2**attempt)

    raise RuntimeError(f"Kimi API failed after {retries} attempts: {last_exc}")


async def chat_complete_long(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 8192,
    response_format: Optional[dict] = None,
) -> tuple[str, int, int]:
    """Use the long-context model for plan generation.

    k2p5 has 262k context and 32k max output — same model as short,
    but called with higher max_tokens for plan generation.
    """
    return await chat_complete(
        messages=messages,
        model=settings.KIMI_MODEL_LONG,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )
