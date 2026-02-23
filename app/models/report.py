import enum
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.pupil import Pupil

# MediumText may not be available in all backends; use Text as fallback
try:
    from sqlalchemy import Text as _Text

    _MediumText = _Text(16777215)  # MariaDB MEDIUMTEXT
except Exception:
    from sqlalchemy import Text

    _MediumText = Text


class ReportType(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Report(Base, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("pupil_id", "report_type", "period_start", name="uq_report_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pupil_id: Mapped[int] = mapped_column(Integer, ForeignKey("pupils.id"), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    content_md: Mapped[str] = mapped_column(_MediumText, nullable=False)
    tasks_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    github_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    github_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_to_telegram: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    pupil: Mapped["Pupil"] = relationship("Pupil", back_populates="reports")
