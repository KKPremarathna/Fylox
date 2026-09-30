from backend.activity.models import TicketActivity

def test_admin_request_ai_category_suggestion(admin_client, customer_ticket, db_session, monkeypatch):
    def fake_suggest(subject, description):
        return {"suggested_category": "BILLING_PAYMENT", "confidence": 0.97}

    monkeypatch.setattr("backend.tickets.routes.suggest_ticket_category", fake_suggest)

    resp = admin_client.post(f"/tickets/{customer_ticket.id}/ai/category-suggestion")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticket_id"] == customer_ticket.id
    assert data["suggested_category"] == "BILLING_PAYMENT"
    assert data["confidence"] == 0.97

    db_session.refresh(customer_ticket)
    assert customer_ticket.ai_suggested_category == "BILLING_PAYMENT"
    assert customer_ticket.ai_category_confidence == 0.97

    activities = db_session.query(TicketActivity).filter_by(
        ticket_id=customer_ticket.id, 
        event_type="AI_CATEGORY_SUGGESTED"
    ).all()
    assert len(activities) == 1

def test_admin_accept_ai_suggestion(admin_client, customer_ticket, db_session):
    customer_ticket.ai_suggested_category = "BILLING_PAYMENT"
    customer_ticket.ai_category_confidence = 0.97
    db_session.commit()

    resp = admin_client.patch(f"/tickets/{customer_ticket.id}/accept-ai-category")
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_category"] == "BILLING_PAYMENT"
    assert data["ai_category_approved"] is True

    db_session.refresh(customer_ticket)
    assert customer_ticket.final_category == "BILLING_PAYMENT"
    assert customer_ticket.ai_category_approved is True

    activities = db_session.query(TicketActivity).filter_by(
        ticket_id=customer_ticket.id, 
        event_type="AI_CATEGORY_ACCEPTED"
    ).all()
    assert len(activities) == 1

def test_admin_override_ai_suggestion(admin_client, customer_ticket, db_session):
    customer_ticket.ai_suggested_category = "BILLING_PAYMENT"
    customer_ticket.ai_category_confidence = 0.97
    db_session.commit()

    resp = admin_client.patch(
        f"/tickets/{customer_ticket.id}/category-review",
        json={"final_category": "TECHNICAL_ISSUE"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_category"] == "TECHNICAL_ISSUE"
    assert data["ai_category_approved"] is False

    activities = db_session.query(TicketActivity).filter_by(
        ticket_id=customer_ticket.id, 
        event_type="AI_CATEGORY_REVIEWED"
    ).all()
    assert len(activities) == 1

def test_admin_manually_set_category(admin_client, customer_ticket, db_session):
    resp = admin_client.patch(
        f"/tickets/{customer_ticket.id}/category-review",
        json={"final_category": "FEATURE_REQUEST"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_category"] == "FEATURE_REQUEST"
    assert data["ai_category_approved"] is None

    activities = db_session.query(TicketActivity).filter_by(
        ticket_id=customer_ticket.id, 
        event_type="CATEGORY_MANUALLY_SET"
    ).all()
    assert len(activities) == 1

def test_customer_forbidden_ai_endpoints(customer_client, customer_ticket):
    resp = customer_client.post(f"/tickets/{customer_ticket.id}/ai/category-suggestion")
    assert resp.status_code == 403

    resp = customer_client.patch(f"/tickets/{customer_ticket.id}/accept-ai-category")
    assert resp.status_code == 403

    resp = customer_client.patch(
        f"/tickets/{customer_ticket.id}/category-review", 
        json={"final_category": "TECHNICAL_ISSUE"}
    )
    assert resp.status_code == 403

def test_accept_ai_category_before_exists(admin_client, customer_ticket):
    resp = admin_client.patch(f"/tickets/{customer_ticket.id}/accept-ai-category")
    assert resp.status_code == 409
