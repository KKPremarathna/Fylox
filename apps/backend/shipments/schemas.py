from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict

class Carrier(str, Enum):
    UPS = "UPS"
    FEDEX = "FEDEX"
    DHL = "DHL"
    USPS = "USPS"
    OTHER = "OTHER"

class ShipmentStatus(str, Enum):
    LABEL_CREATED = "LABEL_CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    EXCEPTION = "EXCEPTION"
    RETURNED = "RETURNED"

class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    carrier: Carrier
    tracking_number: str
    status: ShipmentStatus
    shipped_at: Optional[datetime] = None
    estimated_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
