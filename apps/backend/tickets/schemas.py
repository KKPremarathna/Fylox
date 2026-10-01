from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


TicketStatus = Literal[
    "OPEN",
    "IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
]


class TicketCreate(BaseModel):
    subject: str = Field(
        min_length=5,
        max_length=150,
        examples=["I was charged twice for order ORD-1042"],
    )
    description: str = Field(
        min_length=10,
        max_length=2000,
        examples=[
            "My card shows two successful payment records "
            "for the same order."
        ],
    )

class TicketCategorySuggestionResponse(BaseModel):
    ticket_id: int
    suggested_category: str
    confidence: float
    reason: Optional[str] = None
    source: Optional[str] = None
    
TicketCategory = Literal[
    "ACCOUNT_SUPPORT",
    "BILLING_PAYMENT",
    "ORDER_SUPPORT",
    "TECHNICAL_ISSUE",
    "FEATURE_REQUEST",
    "HOW_TO_SUPPORT",
    "GENERAL_SUPPORT",
    "OTHER",
]


class TicketCategoryReview(BaseModel):
    final_category: TicketCategory

class TicketResponse(BaseModel):
    id: int
    customer_id: int
    assigned_admin_id: Optional[int]
    subject: str
    description: str
    status: TicketStatus
    ai_suggested_category: Optional[str]
    ai_category_confidence: Optional[float]
    final_category: Optional[str]
    ai_category_approved: Optional[bool]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)