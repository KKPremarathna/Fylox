from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, PlainSerializer
from typing_extensions import Annotated


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    CARD = "CARD"
    PAYPAL = "PAYPAL"
    BANK_TRANSFER = "BANK_TRANSFER"


StringDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda d: f"{d:.2f}", return_type=str, when_used="json"),
]


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    provider_reference: str
    amount: StringDecimal
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
