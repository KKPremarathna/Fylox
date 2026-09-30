from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class RefundReviewCreate(BaseModel):
    ticket_id: int
    reason: str


class ApprovalDecisionPatch(BaseModel):
    status: ApprovalStatus
    reviewer_note: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    id: int
    ticket_id: int
    order_id: int
    request_type: str
    status: ApprovalStatus
    requested_by_user_id: int
    reviewed_by_user_id: Optional[int] = None
    reason: str
    evidence_json: dict
    reviewer_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalPaginatedResponse(BaseModel):
    items: list[ApprovalRequestResponse]
    total: int
    limit: int
    offset: int
