from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.go_getter import GoGetter
    from app.models.plan import Plan

import enum


class VacationType(str, enum.Enum):
    summer = "summer"
    winter = "winter"
    spring = "spring"
    autumn = "autumn"
    other = "other"


class TargetStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class Target(Base, TimestampMixin):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    go_getter_id: Mapped[int] = mapped_column(Integer, ForeignKey("go_getters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    vacation_type: Mapped[VacationType] = mapped_column(
        Enum(VacationType), nullable=False, default=VacationType.summer
    )
    vacation_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    status: Mapped[TargetStatus] = mapped_column(
        Enum(TargetStatus), nullable=False, default=TargetStatus.active
    )

    # Relationships
    go_getter: Mapped["GoGetter"] = relationship("GoGetter", back_populates="targets")
    plans: Mapped[list["Plan"]] = relationship("Plan", back_populates="target")
