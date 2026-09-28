from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    subject: str = Field(
        min_length=5,
        max_length=150,
        examples=["I was charged twice for order ORD-1042"],
    )
    description: str = Field(
        min_length=10,
        max_length=2000,
        examples=["My card shows two successful payment records for the same order."],
    )


class TicketStatusUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED"]


class TicketResponse(BaseModel):
    id: int
    customer_id: int
    subject: str
    description: str
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)