from backend.activity.models import TicketActivity
from backend.ai.models import BillingAnalysisRecord

def test_admin_billing_analysis_success(admin_client, customer_ticket, customer_order, db_session):
    resp = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_id"] == customer_order.id
    assert "summary" in data
    assert data["requires_human_review"] is True
    assert data["analysis_source"] == "LLM"
    assert data["admin_id"] is not None

    # Verify no ticket message created
    from backend.messages.models import TicketMessage
    msgs = db_session.query(TicketMessage).filter_by(ticket_id=customer_ticket.id, sender_type="AI").all()
    assert len(msgs) == 0
    
    # Verify BillingAnalysisRecord
    record = db_session.query(BillingAnalysisRecord).filter_by(ticket_id=customer_ticket.id).first()
    assert record.order_id == customer_order.id
    assert record.requires_human_review is True

    # Verify Activity
    activity = db_session.query(TicketActivity).filter_by(
        ticket_id=customer_ticket.id, 
        event_type="BILLING_ANALYSIS_GENERATED"
    ).first()
    assert activity is not None
    assert "generated an AI Billing Analysis" in activity.message
    # Make sure we didn't dump JSON in activity
    assert "{" not in activity.message


def test_customer_forbidden_billing_analysis(customer_client, customer_ticket, customer_order):
    resp = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id}
    )
    assert resp.status_code == 403


def test_reject_other_customer_order(admin_client, customer_ticket, second_customer_order):
    resp = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": second_customer_order.id}
    )
    assert resp.status_code == 400
    assert "does not belong" in resp.json()["detail"]


def test_provider_hallucinates_evidence_triggers_fallback(admin_client, customer_ticket, customer_order, db_session):
    # We update the ticket text to trigger the hallucinate mock
    customer_ticket.description = "HALLUCINATE_EVIDENCE"
    db_session.commit()
    
    resp = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_source"] == "FALLBACK"
    assert data["requires_human_review"] is True
    assert "hallucinated evidence ID" in data["fallback_reason"]


def test_provider_hallucinates_policy_triggers_fallback(admin_client, customer_ticket, customer_order, db_session):
    customer_ticket.description = "HALLUCINATE_POLICY"
    db_session.commit()
    
    resp = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_source"] == "FALLBACK"
    assert data["requires_human_review"] is True
    assert "hallucinated policy ID" in data["fallback_reason"]


def test_provider_failure_triggers_fallback(admin_client, customer_ticket, customer_order, db_session):
    customer_ticket.description = "FAIL_PROVIDER"
    db_session.commit()
    
    resp = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_source"] == "FALLBACK"
    assert data["requires_human_review"] is True
    assert "timeout" in data["fallback_reason"].lower()


def test_model_requires_review_false_overridden(admin_client, customer_ticket, customer_order, db_session):
    customer_ticket.description = "REQUIRE_REVIEW_FALSE"
    db_session.commit()
    
    resp = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["requires_human_review"] is True
