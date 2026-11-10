from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    __table_args__ = (
        CheckConstraint(
            "(sender_type = 'AI' AND sender_id IS NULL) OR (sender_type != 'AI' AND sender_id IS NOT NULL)",
            name="ck_ticket_messages_sender_attribution",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )

    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )