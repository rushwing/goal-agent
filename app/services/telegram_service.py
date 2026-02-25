"""Telegram Bot API client (httpx async)."""

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_message(
    chat_id: int | str,
    text: str,
    bot_token: str,
    parse_mode: str = "Markdown",
    disable_notification: bool = False,
) -> bool:
    """Send a Telegram message. Returns True on success."""
    url = TELEGRAM_API.format(token=bot_token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Telegram send_message failed (chat=%s): %s", chat_id, exc)
        return False


async def send_to_go_getter(chat_id: int | str, text: str) -> bool:
    """Send DM via the go getter bot."""
    if not settings.TELEGRAM_GO_GETTER_BOT_TOKEN:
        logger.warning("TELEGRAM_GO_GETTER_BOT_TOKEN not configured")
        return False
    return await send_message(chat_id, text, bot_token=settings.TELEGRAM_GO_GETTER_BOT_TOKEN)


async def send_to_best_pal(chat_id: int | str, text: str) -> bool:
    """Send DM via the best pal bot."""
    if not settings.TELEGRAM_BEST_PAL_BOT_TOKEN:
        logger.warning("TELEGRAM_BEST_PAL_BOT_TOKEN not configured")
        return False
    return await send_message(chat_id, text, bot_token=settings.TELEGRAM_BEST_PAL_BOT_TOKEN)


async def send_to_group(text: str) -> bool:
    """Send message to the configured Telegram group."""
    if not settings.TELEGRAM_GROUP_CHAT_ID:
        logger.warning("TELEGRAM_GROUP_CHAT_ID not configured")
        return False
    return await send_message(
        settings.TELEGRAM_GROUP_CHAT_ID,
        text,
        bot_token=settings.TELEGRAM_BEST_PAL_BOT_TOKEN,
    )
