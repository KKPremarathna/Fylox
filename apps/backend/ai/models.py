from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class BillingAnalysisRecord(Base):
    __tablename__ = "billing_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_next_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reply_draft: Mapped[str] = mapped_column(Text, nullable=False)
    
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    policy_source_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)

    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    analysis_source: Mapped[str] = mapped_column(String(100), nullable=False, default="LLM")
    fallback_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    ticket = relationship("Ticket", foreign_keys=[ticket_id])
    order = relationship("Order", foreign_keys=[order_id])
    admin = relationship("User", foreign_keys=[admin_id])
