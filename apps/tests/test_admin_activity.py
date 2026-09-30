"""
Tests for GET /admin/activity
"""

from datetime import datetime, timezone

from backend.activity.models import TicketActivity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_activity(
    db_session,
    ticket,
    actor,
    event_type: str = "TICKET_CREATED",
    message: str = "Ticket created.",
    created_at: datetime | None = None,
) -> TicketActivity:
    kwargs: dict = dict(
        ticket_id=ticket.id,
        actor_id=actor.user_id,
        event_type=event_type,
        message=message,
    )
    if created_at is not None:
        kwargs["created_at"] = created_at
    activity = TicketActivity(**kwargs)
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)
    return activity


# ---------------------------------------------------------------------------
# Test A – Admin can list activity and receives enriched fields
# ---------------------------------------------------------------------------

def test_admin_list_activity_enriched(admin_client, customer_ticket, admin_user, db_session):
    _seed_activity(
        db_session,
        ticket=customer_ticket,
        actor=admin_user,
        event_type="TICKET_CREATED",
        message="Ticket created.",
    )

    resp = admin_client.get("/admin/activity")
    assert resp.status_code == 200

    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1
    assert body["limit"] == 20
    assert body["offset"] == 0

    item = next(i for i in body["items"] if i["ticket_id"] == customer_ticket.id)
    assert item["ticket_subject"] == customer_ticket.subject
    assert item["actor_id"] == admin_user.user_id
    assert item["actor_username"] == admin_user.username
    assert item["event_type"] == "TICKET_CREATED"
    assert item["message"] == "Ticket created."


# ---------------------------------------------------------------------------
# Test B – ticket_id filter
# ---------------------------------------------------------------------------

def test_admin_filter_by_ticket_id(
    admin_client, customer_ticket, customer_user, admin_user, db_session
):
    from backend.tickets.models import Ticket

    other_ticket = Ticket(
        customer_id=customer_user.user_id,
        subject="Another ticket",
        description="Another description",
        status="OPEN",
    )
    db_session.add(other_ticket)
    db_session.commit()
    db_session.refresh(other_ticket)

    _seed_activity(db_session, ticket=customer_ticket, actor=admin_user, event_type="TICKET_CREATED")
    _seed_activity(db_session, ticket=other_ticket, actor=admin_user, event_type="TICKET_CREATED")

    resp = admin_client.get(f"/admin/activity?ticket_id={customer_ticket.id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["ticket_id"] == customer_ticket.id


# ---------------------------------------------------------------------------
# Test C – event_type filter
# ---------------------------------------------------------------------------

def test_admin_filter_by_event_type(admin_client, customer_ticket, admin_user, db_session):
    _seed_activity(db_session, ticket=customer_ticket, actor=admin_user, event_type="TICKET_CREATED")
    _seed_activity(db_session, ticket=customer_ticket, actor=admin_user, event_type="TICKET_RESOLVED")

    resp = admin_client.get("/admin/activity?event_type=TICKET_RESOLVED")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["event_type"] == "TICKET_RESOLVED"


# ---------------------------------------------------------------------------
# Test D – start_date / end_date filter
# ---------------------------------------------------------------------------

def test_admin_filter_by_date_range(admin_client, customer_ticket, admin_user, db_session):
    early = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    late  = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    _seed_activity(db_session, ticket=customer_ticket, actor=admin_user, event_type="OLD_EVENT", created_at=early)
    _seed_activity(db_session, ticket=customer_ticket, actor=admin_user, event_type="NEW_EVENT", created_at=late)

    resp = admin_client.get(
        "/admin/activity"
        "?start_date=2024-06-01T00:00:00Z"
        "&end_date=2025-06-01T00:00:00Z"
    )
    assert resp.status_code == 200

    body = resp.json()
    event_types = {i["event_type"] for i in body["items"]}
    assert "NEW_EVENT" in event_types
    assert "OLD_EVENT" not in event_types


# ---------------------------------------------------------------------------
# Test E – invalid date range returns 422
# ---------------------------------------------------------------------------

def test_admin_invalid_date_range_returns_422(admin_client):
    resp = admin_client.get(
        "/admin/activity"
        "?start_date=2025-12-01T00:00:00Z"
        "&end_date=2025-01-01T00:00:00Z"
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test F – pagination returns correct total, limit, offset, and non-overlapping items
# ---------------------------------------------------------------------------

def test_admin_pagination(admin_client, customer_ticket, admin_user, db_session):
    # Seed 5 activity records
    for i in range(5):
        _seed_activity(
            db_session,
            ticket=customer_ticket,
            actor=admin_user,
            event_type="TICKET_CREATED",
            message=f"Event {i}",
        )

    # Page 1: limit=2, offset=0
    resp1 = admin_client.get("/admin/activity?limit=2&offset=0")
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["total"] >= 5
    assert body1["limit"] == 2
    assert body1["offset"] == 0
    assert len(body1["items"]) == 2

    # Page 2: limit=2, offset=2
    resp2 = admin_client.get("/admin/activity?limit=2&offset=2")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["total"] == body1["total"]
    assert body2["limit"] == 2
    assert body2["offset"] == 2
    assert len(body2["items"]) == 2

    # Pages must not overlap
    ids1 = {i["id"] for i in body1["items"]}
    ids2 = {i["id"] for i in body2["items"]}
    assert ids1.isdisjoint(ids2)


# ---------------------------------------------------------------------------
# Test G – customer gets 403
# ---------------------------------------------------------------------------

def test_customer_cannot_list_admin_activity(customer_client):
    resp = customer_client.get("/admin/activity")
    assert resp.status_code == 403
