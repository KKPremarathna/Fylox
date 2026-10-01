from backend.shipments.models import Shipment


def test_get_shipments_owner_success(customer_client, customer_order, customer_shipment):
    res = customer_client.get(f"/orders/{customer_order.id}/shipments")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == customer_shipment.id
    assert data[0]["order_id"] == customer_order.id
    assert data[0]["tracking_number"] == customer_shipment.tracking_number


def test_get_shipments_admin_success(admin_client, customer_order, customer_shipment):
    res = admin_client.get(f"/orders/{customer_order.id}/shipments")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == customer_shipment.id
    # Ensure tracking number and other properties are not masked from admins by default here
    assert data[0]["tracking_number"] == customer_shipment.tracking_number


def test_get_shipments_other_customer_blocked(second_customer_client, customer_order):
    res = second_customer_client.get(f"/orders/{customer_order.id}/shipments")
    assert res.status_code == 403
    assert "Not allowed" in res.json()["detail"]


def test_get_shipments_missing_order(customer_client):
    res = customer_client.get("/orders/99999/shipments")
    assert res.status_code == 404
    assert "Order not found" in res.json()["detail"]


def test_latest_shipment_success(customer_client, customer_order, customer_shipment, db_session):
    # Add a newer shipment to the DB to ensure sorting works correctly
    newer = Shipment(
        order_id=customer_order.id,
        carrier="DHL",
        tracking_number="999888777",
        status="LABEL_CREATED"
    )
    db_session.add(newer)
    db_session.commit()
    db_session.refresh(newer)

    # 1. Full List sorting validation
    list_res = customer_client.get(f"/orders/{customer_order.id}/shipments")
    list_data = list_res.json()
    assert len(list_data) == 2
    assert list_data[0]["id"] == newer.id
    assert list_data[1]["id"] == customer_shipment.id
    
    # 2. Latest specific validation
    latest_res = customer_client.get(f"/orders/{customer_order.id}/shipments/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["id"] == newer.id


def test_latest_shipment_not_found(customer_client, customer_order):
    # Order exists, but has no shipments
    res = customer_client.get(f"/orders/{customer_order.id}/shipments/latest")
    assert res.status_code == 404
    assert "No shipments found" in res.json()["detail"]
