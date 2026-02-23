"""Kimi AI (Moonshot) LLM client – OpenAI-compatible."""
import asyncio
import logging
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Respect Kimi rate limits: max 3 concurrent requests
_semaphore = asyncio.Semaphore(3)

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url=settings.KIMI_BASE_URL,
        )
    return _client


async def chat_complete(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
    retries: int = 3,
) -> tuple[str, int, int]:
    """
    Call Kimi API with rate limiting and retry.

    Returns:
        (content, prompt_tokens, completion_tokens)
    """
    if model is None:
        model = settings.KIMI_MODEL_SHORT

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            async with _semaphore:
                response = await get_client().chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            return content, prompt_tokens, completion_tokens
        except httpx.ConnectError as exc:
            logger.warning("Kimi API connection error (attempt %d): %s", attempt + 1, exc)
            last_exc = exc
        except Exception as exc:
            logger.warning("Kimi API error (attempt %d): %s", attempt + 1, exc)
            last_exc = exc
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)

    raise RuntimeError(f"Kimi API failed after {retries} attempts: {last_exc}")


async def chat_complete_long(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 8192,
    response_format: Optional[dict] = None,
) -> tuple[str, int, int]:
    """Use the long-context model (32k) for plan generation."""
    return await chat_complete(
        messages=messages,
        model=settings.KIMI_MODEL_LONG,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )
