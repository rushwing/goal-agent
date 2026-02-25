"""Notification persistence and dispatch."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationStatus,
    RecipientType,
    NotificationChannel,
    NotificationType,
)
from app.services import telegram_service

logger = logging.getLogger(__name__)


async def send_and_log(
    db: AsyncSession,
    recipient_type: RecipientType,
    recipient_id: int | None,
    chat_id: int | str,
    message_text: str,
    notification_type: NotificationType,
    channel: NotificationChannel,
    use_go_getter_bot: bool = False,
) -> Notification:
    notification = Notification(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        channel=channel,
        telegram_chat_id=int(chat_id) if str(chat_id).lstrip("-").isdigit() else None,
        message_text=message_text,
        notification_type=notification_type,
        status=NotificationStatus.pending,
    )
    db.add(notification)
    await db.flush()

    try:
        if channel == NotificationChannel.telegram_group:
            ok = await telegram_service.send_to_group(message_text)
        elif use_go_getter_bot:
            ok = await telegram_service.send_to_go_getter(chat_id, message_text)
        else:
            ok = await telegram_service.send_to_best_pal(chat_id, message_text)

        notification.status = NotificationStatus.sent if ok else NotificationStatus.failed
        notification.sent_at = datetime.utcnow()
    except Exception as exc:
        logger.error("Notification dispatch failed: %s", exc)
        notification.status = NotificationStatus.failed
        notification.error_message = str(exc)[:500]

    await db.flush()
    return notification
