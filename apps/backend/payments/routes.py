from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.orders.service import get_order_for_owner_or_admin
from backend.payments.models import Payment
from backend.payments.schemas import PaymentResponse
from backend.security import get_current_user
from backend.users.models import User

router = APIRouter(
    prefix="/orders/{order_id}/payments",
    tags=["Payments"],
)


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Authorize: confirm the caller has rights to view this specific order
    authorized_order = get_order_for_owner_or_admin(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )

    # 2. Fetch payments exclusively tied to this authorized order
    statement = (
        select(Payment)
        .where(Payment.order_id == authorized_order.id)
        .order_by(
            Payment.created_at.desc(),
            Payment.id.desc(),
        )
    )

    return db.scalars(statement).all()
