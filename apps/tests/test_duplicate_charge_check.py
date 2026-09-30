from decimal import Decimal
import pytest
from backend.payments.models import Payment

def test_duplicate_check_one_success_no_duplicate(customer_client, customer_order, customer_payment):
    """1 successful payment -> no duplicate."""
    resp = customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_possible_duplicate"] is False
    assert data["successful_payment_count"] == 1
    assert len(data["duplicate_groups"]) == 0
    assert data["message"] == "We did not find multiple matching successful payments for this order."


def test_duplicate_check_two_matching_success(customer_client, customer_order, customer_payment, db_session):
    """2 matching successful payments -> possible duplicate."""
    # customer_payment is already 149.99 USD SUCCEEDED
    p2 = Payment(
        order_id=customer_order.id,
        provider_reference="ch_duplicate",
        amount=Decimal("149.99"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD",
    )
    db_session.add(p2)
    db_session.commit()

    resp = customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_possible_duplicate"] is True
    assert data["successful_payment_count"] == 2
    assert len(data["duplicate_groups"]) == 1
    assert data["duplicate_groups"][0]["amount"] == "149.99"
    assert data["duplicate_groups"][0]["currency"] == "USD"
    assert data["duplicate_groups"][0]["payment_count"] == 2
    assert data["message"] == "We found multiple successful payments with the same amount. A support agent can review this request."


def test_duplicate_check_different_amounts(customer_client, customer_order, customer_payment, db_session):
    """Different amounts -> no duplicate group."""
    p2 = Payment(
        order_id=customer_order.id,
        provider_reference="ch_diff_amt",
        amount=Decimal("50.00"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD",
    )
    db_session.add(p2)
    db_session.commit()

    resp = customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_possible_duplicate"] is False
    assert data["successful_payment_count"] == 2
    assert len(data["duplicate_groups"]) == 0


def test_duplicate_check_different_currency(customer_client, customer_order, customer_payment, db_session):
    """Different currency -> no duplicate group."""
    p2 = Payment(
        order_id=customer_order.id,
        provider_reference="ch_diff_curr",
        amount=Decimal("149.99"),
        currency="EUR",
        status="SUCCEEDED",
        payment_method="CARD",
    )
    db_session.add(p2)
    db_session.commit()

    resp = customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_possible_duplicate"] is False
    assert data["successful_payment_count"] == 2
    assert len(data["duplicate_groups"]) == 0


def test_duplicate_check_ignores_non_successful(customer_client, customer_order, customer_payment, db_session):
    """failed/pending/refunded payments ignored."""
    for status, ref in [("FAILED", "f1"), ("PENDING", "p1"), ("REFUNDED", "r1")]:
        db_session.add(Payment(
            order_id=customer_order.id,
            provider_reference=ref,
            amount=Decimal("149.99"),
            currency="USD",
            status=status,
            payment_method="CARD",
        ))
    db_session.commit()

    resp = customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_possible_duplicate"] is False
    assert data["successful_payment_count"] == 1
    assert len(data["duplicate_groups"]) == 0


def test_duplicate_check_authorization_non_owner(second_customer_client, customer_order):
    """non-owner receives 403."""
    resp = second_customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 403

def test_duplicate_check_authorization_missing(customer_client):
    """missing order returns 404."""
    resp = customer_client.get(f"/orders/999999/duplicate-charge-check")
    assert resp.status_code == 404

def test_duplicate_check_authorization_admin(admin_client, customer_order):
    """admin can check anyone's order."""
    resp = admin_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200


def test_duplicate_check_no_provider_leak(customer_client, customer_order, customer_payment, db_session):
    """response does not expose provider_reference."""
    # Even if duplicate
    p2 = Payment(
        order_id=customer_order.id,
        provider_reference="ch_secret_duplicate",
        amount=Decimal("149.99"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD",
    )
    db_session.add(p2)
    db_session.commit()

    resp = customer_client.get(f"/orders/{customer_order.id}/duplicate-charge-check")
    assert resp.status_code == 200
    
    body = resp.text
    assert customer_payment.provider_reference not in body
    assert "ch_secret_duplicate" not in body
