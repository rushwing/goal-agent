import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RecipientType(str, enum.Enum):
    go_getter = "go_getter"
    best_pal = "best_pal"
    group = "group"


class NotificationChannel(str, enum.Enum):
    telegram_dm = "telegram_dm"
    telegram_group = "telegram_group"


class NotificationType(str, enum.Enum):
    daily_tasks = "daily_tasks"
    evening_reminder = "evening_reminder"
    weekly_report = "weekly_report"
    monthly_report = "monthly_report"
    achievement = "achievement"
    praise = "praise"
    generic = "generic"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_type: Mapped[RecipientType] = mapped_column(Enum(RecipientType), nullable=False)
    recipient_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, default=NotificationType.generic
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), nullable=False, default=NotificationStatus.pending
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
