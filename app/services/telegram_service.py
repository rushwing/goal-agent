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


async def send_to_pupil(chat_id: int | str, text: str) -> bool:
    """Send DM via the pupil bot."""
    if not settings.TELEGRAM_PUPIL_BOT_TOKEN:
        logger.warning("TELEGRAM_PUPIL_BOT_TOKEN not configured")
        return False
    return await send_message(chat_id, text, bot_token=settings.TELEGRAM_PUPIL_BOT_TOKEN)


async def send_to_parent(chat_id: int | str, text: str) -> bool:
    """Send DM via the parent bot."""
    if not settings.TELEGRAM_PARENT_BOT_TOKEN:
        logger.warning("TELEGRAM_PARENT_BOT_TOKEN not configured")
        return False
    return await send_message(chat_id, text, bot_token=settings.TELEGRAM_PARENT_BOT_TOKEN)


async def send_to_group(text: str) -> bool:
    """Send message to the configured Telegram group."""
    if not settings.TELEGRAM_GROUP_CHAT_ID:
        logger.warning("TELEGRAM_GROUP_CHAT_ID not configured")
        return False
    return await send_message(
        settings.TELEGRAM_GROUP_CHAT_ID,
        text,
        bot_token=settings.TELEGRAM_PARENT_BOT_TOKEN,
    )
