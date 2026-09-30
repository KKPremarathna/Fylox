import pytest
from sqlalchemy.exc import IntegrityError


def test_orders_listed_for_customer(customer_client, customer_order):
    """Customer list returns only their orders, with total_amount serialized as a string."""
    resp = customer_client.get("/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == customer_order.id
    
    # Confirm exact monetary precision serialization (string)
    assert data[0]["total_amount"] == "149.99"


def test_orders_listed_for_admin(admin_client, customer_order, second_customer_order):
    """Admin sees all orders, newest first."""
    resp = admin_client.get("/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Newest first means second_customer_order (id 2) is before customer_order (id 1)
    assert data[0]["id"] == second_customer_order.id
    assert data[1]["id"] == customer_order.id


def test_get_order_owner(customer_client, customer_order):
    """Owner can retrieve their own order."""
    resp = customer_client.get(f"/orders/{customer_order.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == customer_order.id
    assert data["order_number"] == customer_order.order_number


def test_get_order_non_owner_blocked(second_customer_client, customer_order):
    """Different customer receives 403 and response does not leak sensitive fields."""
    resp = second_customer_client.get(f"/orders/{customer_order.id}")
    assert resp.status_code == 403
    
    body = resp.text
    assert customer_order.order_number not in body
    assert "149.99" not in body
    assert customer_order.status not in body


def test_get_order_admin(admin_client, customer_order):
    """Admin can retrieve any order."""
    resp = admin_client.get(f"/orders/{customer_order.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == customer_order.id


def test_get_order_missing(customer_client):
    """Missing order returns 404."""
    resp = customer_client.get("/orders/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Order not found"


def test_order_number_uniqueness_constraint(db_session, customer_user, customer_order):
    """Confirm DB strictly enforces order_number uniqueness."""
    from backend.orders.models import Order
    from decimal import Decimal
    
    duplicate_order = Order(
        order_number=customer_order.order_number,  # deliberate collision
        customer_id=customer_user.user_id,
        status="PENDING",
        total_amount=Decimal("100.00"),
        currency="USD",
    )
    db_session.add(duplicate_order)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
