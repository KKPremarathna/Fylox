from collections import defaultdict
from backend.payments.models import Payment
from backend.payments.schemas import DuplicateChargeCheckResponse, DuplicateGroup


def check_duplicate_charges(
    order_id: int, payments: list[Payment]
) -> DuplicateChargeCheckResponse:
    """
    Pure business logic function examining a list of payments to identify likely duplicates.
    Does not issue queries, update statuses, execute refunds, or use Request/Response components.
    """
    successful_payments = [p for p in payments if p.status == "SUCCEEDED"]
    
    # Group by (amount, currency)
    groupings: dict[tuple[float, str], int] = defaultdict(int)
    for p in successful_payments:
        groupings[(p.amount, p.currency)] += 1

    duplicate_groups: list[DuplicateGroup] = []
    has_possible_duplicate = False

    for (amount, currency), count in groupings.items():
        if count >= 2:
            duplicate_groups.append(
                DuplicateGroup(
                    amount=amount,
                    currency=currency,
                    payment_count=count,
                )
            )
            has_possible_duplicate = True

    # Deterministic sorting: amount descending, currency ascending
    duplicate_groups.sort(key=lambda g: (-g.amount, g.currency))

    if has_possible_duplicate:
        message = "We found multiple successful payments with the same amount. A support agent can review this request."
    else:
        message = "We did not find multiple matching successful payments for this order."

    return DuplicateChargeCheckResponse(
        order_id=order_id,
        has_possible_duplicate=has_possible_duplicate,
        successful_payment_count=len(successful_payments),
        duplicate_groups=duplicate_groups,
        message=message,
    )
