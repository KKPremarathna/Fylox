from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


if TYPE_CHECKING:
    from backend.users.models import User


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    assigned_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="OPEN",
    )

    ai_suggested_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    ai_category_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    final_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    ai_category_approved: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    customer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[customer_id],
        back_populates="tickets",
    )

    assigned_admin: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_admin_id],
    )