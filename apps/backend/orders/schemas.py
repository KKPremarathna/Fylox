from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, PlainSerializer
from typing_extensions import Annotated


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# Ensures that the decimal is preserved and formatted as a JSON string
# like "149.99" during dumping, rather than a float losing precision.
StringDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda d: f"{d:.2f}", return_type=str, when_used="json"),
]


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    status: OrderStatus
    total_amount: StringDecimal
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
