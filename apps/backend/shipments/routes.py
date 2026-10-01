from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.orders.service import get_order_for_owner_or_admin
from backend.security import get_current_user
from backend.shipments.models import Shipment
from backend.shipments.schemas import ShipmentResponse
from backend.users.models import User

router = APIRouter(
    prefix="/orders/{order_id}/shipments",
    tags=["Shipments"]
)

@router.get("", response_model=list[ShipmentResponse])
def get_shipments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    authorized_order = get_order_for_owner_or_admin(
        db=db, 
        order_id=order_id, 
        current_user=current_user
    )

    # Sort descending deterministically
    statement = (
        select(Shipment)
        .where(Shipment.order_id == authorized_order.id)
        .order_by(Shipment.created_at.desc(), Shipment.id.desc())
    )
    return db.scalars(statement).all()

@router.get("/latest", response_model=ShipmentResponse)
def get_latest_shipment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    authorized_order = get_order_for_owner_or_admin(
        db=db, 
        order_id=order_id, 
        current_user=current_user
    )

    # Sort descending deterministically exactly matching standard listing
    statement = (
        select(Shipment)
        .where(Shipment.order_id == authorized_order.id)
        .order_by(Shipment.created_at.desc(), Shipment.id.desc())
        .limit(1)
    )
    latest = db.scalars(statement).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No shipments found for this order")
    
    return latest
