from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.orders.models import Order
from backend.orders.schemas import OrderResponse
from backend.orders.service import get_order_for_owner_or_admin
from backend.security import get_current_user
from backend.users.models import User


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.get("", response_model=list[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Sort created_at descending, then id descending as tie-breaker per requirements
    statement = select(Order).order_by(
        Order.created_at.desc(),
        Order.id.desc(),
    )

    if current_user.role == "CUSTOMER":
        statement = statement.where(Order.customer_id == current_user.user_id)
    # Admin sees all orders

    return db.scalars(statement).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_order_for_owner_or_admin(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )
