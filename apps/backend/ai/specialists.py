import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai.schemas import RoutingCategory
from backend.orders.models import Order
from backend.policies.service import search_policies


ORDER_REFERENCE_PATTERN = re.compile(
    r"\border\s*#\s*([A-Za-z0-9][A-Za-z0-9_-]{0,49})\b"
    r"|\border\s+(?:number|no\.?)\s*[:#]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9_-]{0,49})\b",
    flags=re.IGNORECASE,
)


def extract_order_numbers(message: str) -> set[str]:
    """
    Extract explicitly labelled public order numbers.

    Supported examples:
    - order #FY-1001
    - order number FY-1001
    - order no: FY-1001

    Bare numbers are not interpreted as order references.
    """
    return {
        match.group(1) or match.group(2)
        for match in ORDER_REFERENCE_PATTERN.finditer(message)
    }


def order_specialist(
    db: Session,
    message: str,
    customer_id: int,
) -> str:
    """
    Return stored order status for the ticket customer only.

    Does not modify orders, infer tracking information,
    or select an order without an explicit reference.
    """
    order_numbers = extract_order_numbers(message)

    if not order_numbers:
        return (
            "Please provide your order number so I can check "
            "the stored order status. "
            "Use a format such as 'order #FY-1001'."
        )

    if len(order_numbers) > 1:
        return (
            "Please provide one order number at a time "
            "so I can check the correct order."
        )

    order_number = next(iter(order_numbers))

    statement = select(Order).where(
        Order.customer_id == customer_id,
        Order.order_number == order_number,
    )

    order = db.scalars(statement).one_or_none()

    if order is None:
        return (
            "I could not find that order under the customer "
            "account linked to this ticket. "
            "Please check the order number and try again."
        )

    return (
        f"The stored status for order #{order.order_number} "
        f"is {order.status}. "
        "This response uses the order record only; "
        "it does not include carrier tracking or "
        "a confirmed delivery estimate."
    )


def billing_specialist(
    db: Session,
    message: str,
    customer_id: int,
) -> str:
    """
    Reserved acknowledgment helper.

    The dispatcher intentionally does not call this function
    for automated billing replies.
    """
    return (
        "Your billing concern requires human review. "
        "This assistant cannot approve or process refunds."
    )


def policy_specialist(
    db: Session,
    message: str,
) -> str:
    """
    Return a retrieved approved-policy excerpt.

    Retrieval alone does not establish eligibility or
    authorize a billing or order action.
    """
    results = search_policies(
        db=db,
        query=message,
    )

    if not results:
        return (
            "I could not find a matching approved policy "
            "excerpt for this question. "
            "Please provide more specific details."
        )

    top = results[0]

    return (
        f"A potentially relevant excerpt from "
        f"'{top.document_title}' "
        f"(policy chunk {top.chunk_id}) states:\n\n"
        f"{top.snippet_text}\n\n"
        "This excerpt alone does not confirm eligibility. "
        "The full applicable policy should be checked "
        "before a decision is made."
    )


def general_specialist(message: str) -> str:
    """
    Ask for clarification without invoking external tools.
    """
    return (
        "Please describe what you need help with, such as "
        "an order status, a billing concern, or a policy "
        "question. For order-status requests, include "
        "your order number."
    )


def run_specialist_delegation(
    db: Session,
    category: RoutingCategory,
    message: str,
    customer_id: int,
) -> str | None:
    """
    Dispatch supported categories to scoped handlers.

    Billing and human escalation intentionally produce
    no automated customer reply through this dispatcher.
    """
    if category == RoutingCategory.ORDER_SUPPORT:
        return order_specialist(
            db=db,
            message=message,
            customer_id=customer_id,
        )

    if category == RoutingCategory.POLICY_SUPPORT:
        return policy_specialist(
            db=db,
            message=message,
        )

    if category == RoutingCategory.GENERAL_SUPPORT:
        return general_specialist(message)

    return None