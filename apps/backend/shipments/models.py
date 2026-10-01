from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    carrier: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # In real world tracking numbers might collide between different carriers occasionally
    # Adding a unique constraint is debated, but let's leave it as just indexed for MVP robustness across mock test data bounds
    tracking_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
