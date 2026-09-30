from decimal import Decimal
import pytest
from backend.activity.models import TicketActivity
from backend.payments.models import Payment
from backend.approvals.models import ApprovalRequest
from sqlalchemy import select


def test_approvals_customer_authorization_failures(
    second_customer_client, customer_order, customer_ticket
):
    """non-owner receives 403 trying to file request against another user's order"""
    resp = second_customer_client.post(
        f"/orders/{customer_order.id}/refund-review-requests",
        json={"ticket_id": customer_ticket.id, "reason": "Refund requested"}
    )
    assert resp.status_code == 403


def test_approvals_cross_ownership_mismatch(
    customer_client, db_session, customer_order, second_customer_user
):
    """Customer tries to file request with THEIR order but someone else's ticket"""
    from backend.tickets.models import Ticket
    
    t2 = Ticket(
        customer_id=second_customer_user.user_id,
        subject="Other user ticket",
        description="description",
        status="OPEN"
    )
    db_session.add(t2)
    db_session.commit()
    db_session.refresh(t2)
    
    resp = customer_client.post(
        f"/orders/{customer_order.id}/refund-review-requests",
        json={"ticket_id": t2.id, "reason": "Refund requested"}
    )
    # Auth fails safely returning 403 on the ticket evaluation boundary FIRST
    assert resp.status_code == 403


def test_approvals_no_duplicates_returns_409(
    customer_client, db_session, customer_order, customer_ticket, customer_payment
):
    """Customer submitting valid match order/ticket but no duplicate charges exist"""
    # Only 1 payment exists here (customer_payment)... NO duplicates
    resp = customer_client.post(
        f"/orders/{customer_order.id}/refund-review-requests",
        json={"ticket_id": customer_ticket.id, "reason": "Refund requested"}
    )
    assert resp.status_code == 409
    assert "not eligible for duplicate refund review" in resp.json()["detail"].lower()
    
    # Assert absolutely NO activity logs triggered
    count = db_session.scalars(select(TicketActivity).where(TicketActivity.ticket_id == customer_ticket.id)).all()
    # Exclude initial messages, specifically check event_type doesn't contain REFUND_REVIEW_REQUESTED
    assert not any(act.event_type == "REFUND_REVIEW_REQUESTED" for act in count)


def test_approvals_duplicate_charge_success_and_concurrency(
    customer_client, db_session, customer_order, customer_ticket, customer_payment
):
    """Successful payload, blocking concurrent submissions structurally"""
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

    resp = customer_client.post(
        f"/orders/{customer_order.id}/refund-review-requests",
        json={"ticket_id": customer_ticket.id, "reason": "Duplicate charged fast!"}
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING"
    assert resp.json()["evidence_json"]["successful_payment_count"] == 2
    
    evidence_txt = str(resp.json()["evidence_json"])
    assert "ch_duplicate" not in evidence_txt
    assert customer_payment.provider_reference not in evidence_txt

    activity = db_session.scalars(
        select(TicketActivity).where(TicketActivity.event_type == "REFUND_REVIEW_REQUESTED")
    ).first()
    assert activity is not None
    assert activity.ticket_id == customer_ticket.id
    
    # Try simultaneous execution replicating duplicate request
    resp2 = customer_client.post(
        f"/orders/{customer_order.id}/refund-review-requests",
        json={"ticket_id": customer_ticket.id, "reason": "Accidental double click"}
    )
    assert resp2.status_code == 409
    
    # Assert a second Activity log wasn't leaked due to rollback
    activities = db_session.scalars(
        select(TicketActivity).where(TicketActivity.event_type == "REFUND_REVIEW_REQUESTED")
    ).all()
    assert len(activities) == 1


def test_approvals_admin_review_missing_rejection_note(
    admin_client, customer_order, customer_ticket, db_session
):
    """Admin evaluates pending but forgets note for rejection => 422"""
    # Create PENDING directly behind the scenes
    req = ApprovalRequest(
        ticket_id=customer_ticket.id,
        order_id=customer_order.id,
        request_type="REFUND_REVIEW",
        status="PENDING",
        requested_by_user_id=customer_ticket.customer_id,
        reason="Test PENDING",
        evidence_json={}
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    
    resp = admin_client.patch(
        f"/admin/approval-requests/{req.id}",
        json={"status": "REJECTED", "reviewer_note": ""}
    )
    assert resp.status_code == 422
    
    # Re-verify failure left DB unaltered
    db_session.refresh(req)
    assert req.status == "PENDING"
    assert not db_session.scalars(
        select(TicketActivity).where(TicketActivity.event_type == "REFUND_REVIEW_REJECTED")
    ).all()


def test_approvals_admin_review_success_and_concurrency(
    admin_client, customer_order, customer_ticket, db_session
):
    """Admin rejects completely successfully, generating logs, stopping secondary admin overwrite"""
    req = ApprovalRequest(
        ticket_id=customer_ticket.id,
        order_id=customer_order.id,
        request_type="REFUND_REVIEW",
        status="PENDING",
        requested_by_user_id=customer_ticket.customer_id,
        reason="Test PENDING",
        evidence_json={}
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    
    resp = admin_client.patch(
        f"/admin/approval-requests/{req.id}",
        json={"status": "REJECTED", "reviewer_note": "False duplicate alert."}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["reviewer_note"] == "False duplicate alert."
    
    # Verify Activity log written
    activity = db_session.scalars(
        select(TicketActivity).where(TicketActivity.event_type == "REFUND_REVIEW_REJECTED")
    ).all()
    assert len(activity) == 1
    
    # Secondary admin attempts to rewrite to APPROVED
    resp2 = admin_client.patch(
        f"/admin/approval-requests/{req.id}",
        json={"status": "APPROVED", "reviewer_note": "I disagree."}
    )
    assert resp2.status_code == 409
    
    activity2 = db_session.scalars(
        select(TicketActivity).where(TicketActivity.event_type == "REFUND_REVIEW_APPROVED")
    ).all()
    # Confirm no log written from the failed attempt
    assert len(activity2) == 0


def test_approvals_delete_ticket_blocked_by_restrict(
    admin_client, customer_order, customer_ticket, db_session
):
    """Deleting a ticket with a tied request blocks completely due to RESTRICT"""
    from sqlalchemy.exc import IntegrityError
    from backend.tickets.models import Ticket
    
    req = ApprovalRequest(
        ticket_id=customer_ticket.id,
        order_id=customer_order.id,
        request_type="REFUND_REVIEW",
        status="PENDING",
        requested_by_user_id=customer_ticket.customer_id,
        reason="Test RESTRICT",
        evidence_json={}
    )
    db_session.add(req)
    db_session.commit()
    
    with pytest.raises(IntegrityError):
        from sqlalchemy import text
        db_session.execute(text("PRAGMA foreign_keys=ON"))
        
        t = db_session.get(Ticket, customer_ticket.id)
        db_session.delete(t)
        db_session.commit()
    db_session.rollback()
