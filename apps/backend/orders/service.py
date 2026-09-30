from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.orders.models import Order
from backend.users.models import User


def get_order_for_owner_or_admin(
    db: Session,
    order_id: int,
    current_user: User,
) -> Order:
    """
    Centralized authorization helper for Order access.

    Returns the Order if the user is an ADMIN or the customer who owns the order.
    Raises 404 "Order not found" if it does not exist.
    Raises 403 "Not allowed to access this order" if the user is a non-owning customer.
    """
    order = db.get(Order, order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    is_owner = order.customer_id == current_user.user_id
    is_admin = current_user.role == "ADMIN"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order",
        )

    return order
