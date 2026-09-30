import pytest
from sqlalchemy.exc import IntegrityError


def test_list_payments_owner(customer_client, customer_order, customer_payment):
    """Owner can list payments properly formatted."""
    resp = customer_client.get(f"/orders/{customer_order.id}/payments")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == customer_payment.id
    
    # Confirm exact monetary formatting
    assert data[0]["amount"] == "149.99"


def test_list_payments_non_owner_403_no_data_leak(
    second_customer_client, customer_order, customer_payment
):
    """Non-owner receives 403 and sees absolutely no payment data."""
    resp = second_customer_client.get(f"/orders/{customer_order.id}/payments")
    assert resp.status_code == 403
    
    body = resp.text
    assert customer_payment.provider_reference not in body
    assert "149.99" not in body
    assert customer_payment.status not in body


def test_list_payments_admin(admin_client, customer_order, customer_payment):
    """Admin can list anyone's payments."""
    resp = admin_client.get(f"/orders/{customer_order.id}/payments")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_payments_missing_order(customer_client):
    """Missing order safely cascades a 404 via the shared service helper."""
    resp = customer_client.get("/orders/999999/payments")
    assert resp.status_code == 404


def test_payments_newest_first_and_isolated(
    customer_client, customer_order, second_customer_order, db_session
):
    """
    Multiple tests:
    - Never blends current user's payments with OTHER orders' payments.
    - Sorts newest (id/created) first.
    """
    from decimal import Decimal
    from backend.payments.models import Payment

    # Create two payments for customer_order
    p1 = Payment(
        order_id=customer_order.id,
        provider_reference="stripe_1",
        amount=Decimal("10.00"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD"
    )
    p2 = Payment(
        order_id=customer_order.id,
        provider_reference="stripe_2",
        amount=Decimal("20.00"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD"
    )
    # Create one payment for second_customer_order
    p3 = Payment(
        order_id=second_customer_order.id,
        provider_reference="stripe_3",
        amount=Decimal("30.00"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD"
    )
    
    db_session.add_all([p1, p2, p3])
    db_session.commit()
    
    resp = customer_client.get(f"/orders/{customer_order.id}/payments")
    assert resp.status_code == 200
    data = resp.json()
    
    # Must only contain 2 items, completely skipping p3
    assert len(data) == 2
    
    # Newest first means p2 comes before p1
    assert data[0]["provider_reference"] == "stripe_2"
    assert data[1]["provider_reference"] == "stripe_1"


def test_payment_provider_reference_uniqueness(db_session, customer_order, customer_payment):
    """Confirm the provider_reference fails strictly on duplicate DB input."""
    from decimal import Decimal
    from backend.payments.models import Payment
    
    duplicate = Payment(
        order_id=customer_order.id,
        provider_reference=customer_payment.provider_reference,  # Deliberate collision
        amount=Decimal("100.00"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD"
    )
    db_session.add(duplicate)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_payment_negative_amount_constraint(db_session, customer_order):
    """Database should reject negatively charged payments."""
    from decimal import Decimal
    from backend.payments.models import Payment
    
    negative = Payment(
        order_id=customer_order.id,
        provider_reference="stripe_neg",
        amount=Decimal("-50.00"),  # Deliberate negative violation
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD"
    )
    db_session.add(negative)
    
    # SQLite enforces this constraint when evaluated in Python DBAPI hooks or strict modes.
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
