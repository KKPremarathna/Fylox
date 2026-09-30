"""
Tests for the sliding-window log rate limiter on
POST /tickets/{ticket_id}/ai/category-suggestion.

Clock control
─────────────
routes.py imports ``get_current_time`` from ``backend.tickets.rate_limit``
and passes it *by name* at call time:

    check_ai_suggestion_rate_limit(user_id, now_fn=get_current_time)

Because it is resolved from the routes module's namespace at call time (not
bound as a default argument at definition time), monkeypatching the name in
that module's namespace is sufficient to control the clock for all tests.

    monkeypatch.setattr("backend.tickets.routes.get_current_time", fake_clock)

The fake clock is a closure over a mutable list ``[t]`` so tests can advance
time by mutating ``t[0]`` without any ``sleep``.
"""

import pytest

from backend.users.models import User


# ── Shared fake ML service ───────────────────────────────────────────────────

def _fake_suggest(subject, description):
    return {"suggested_category": "BILLING_PAYMENT", "confidence": 0.97}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_clock(start: float = 0.0):
    """Return a (clock_fn, time_ref) pair.  Mutate time_ref[0] to advance."""
    t = [start]
    return lambda: t[0], t


def _seed_admin(db_session, username="admin2", email="admin2@example.com"):
    user = User(
        username=username,
        email=email,
        password_hash="fakehash",
        role="ADMIN",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Test 1: first 10 requests all succeed ────────────────────────────────────

def test_first_ten_requests_succeed(admin_client, customer_ticket, monkeypatch):
    """
    With a frozen clock the sliding window never expires, so the first 10
    calls must all return 200.
    """
    clock, t = _make_clock(0.0)
    monkeypatch.setattr("backend.tickets.routes.get_current_time", clock)
    monkeypatch.setattr("backend.tickets.routes.suggest_ticket_category", _fake_suggest)

    for i in range(10):
        # Advance time slightly so timestamps are distinct, but well within 60 s.
        t[0] = float(i)
        resp = admin_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 200, f"Request {i + 1} unexpectedly failed"


# ── Test 2: 11th request returns 429 with Retry-After ────────────────────────

def test_eleventh_request_returns_429_with_retry_after(
    admin_client, customer_ticket, monkeypatch
):
    """
    After 10 accepted calls the log is full; the 11th call must be rejected
    with 429 and include a Retry-After header whose value is a positive integer
    not exceeding the window length (60 s).
    """
    clock, t = _make_clock(0.0)
    monkeypatch.setattr("backend.tickets.routes.get_current_time", clock)
    monkeypatch.setattr("backend.tickets.routes.suggest_ticket_category", _fake_suggest)

    for i in range(10):
        t[0] = float(i)
        resp = admin_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 200

    # 11th call — clock stays at 9.0 so none of the log entries have expired.
    resp = admin_client.post(
        f"/tickets/{customer_ticket.id}/ai/category-suggestion"
    )
    assert resp.status_code == 429

    retry_after = int(resp.headers["Retry-After"])
    assert 1 <= retry_after <= 60, (
        f"Retry-After should be 1–60 s, got {retry_after}"
    )

    body = resp.json()
    assert "rate limit" in body["detail"].lower()


# ── Test 3: two admins have independent quotas ────────────────────────────────

def test_two_admins_have_independent_quotas(
    admin_client, admin_user, customer_ticket, db_session, monkeypatch
):
    """
    Exhausting admin-1's quota must not affect admin-2.
    """
    from backend.security import get_current_user
    from backend.main import app

    clock, t = _make_clock(0.0)
    monkeypatch.setattr("backend.tickets.routes.get_current_time", clock)
    monkeypatch.setattr("backend.tickets.routes.suggest_ticket_category", _fake_suggest)

    # Exhaust admin-1's quota (10 calls).
    for i in range(10):
        t[0] = float(i)
        resp = admin_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 200

    # Confirm admin-1 is now rate-limited.
    resp = admin_client.post(
        f"/tickets/{customer_ticket.id}/ai/category-suggestion"
    )
    assert resp.status_code == 429

    # Seed a second admin and switch the dependency override.
    admin2 = _seed_admin(db_session)
    app.dependency_overrides[get_current_user] = lambda: admin2

    try:
        t[0] = 10.0
        resp = admin_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 200, (
            "admin-2's first request should succeed independently of admin-1's quota"
        )
    finally:
        # Restore to admin-1 so other test teardown is unaffected.
        app.dependency_overrides[get_current_user] = lambda: admin_user


# ── Test 4: customer still receives 403, not 429 ─────────────────────────────

def test_customer_receives_403_not_429(customer_client, customer_ticket):
    """
    The role check fires before rate-limit accounting; customers must always
    receive 403 regardless of quota state.
    """
    # Make many calls — none should ever become 429.
    for _ in range(15):
        resp = customer_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 403


# ── Test 5: window expiry resets quota ───────────────────────────────────────

def test_quota_resets_after_window_expires(
    admin_client, customer_ticket, monkeypatch
):
    """
    After advancing the clock past the 60-second window all log entries expire
    and the next call succeeds — no sleep required.
    """
    clock, t = _make_clock(0.0)
    monkeypatch.setattr("backend.tickets.routes.get_current_time", clock)
    monkeypatch.setattr("backend.tickets.routes.suggest_ticket_category", _fake_suggest)

    # Exhaust quota: 10 calls at t = 0 … 9.
    for i in range(10):
        t[0] = float(i)
        resp = admin_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 200

    # Confirm rate-limited at t = 9.
    resp = admin_client.post(
        f"/tickets/{customer_ticket.id}/ai/category-suggestion"
    )
    assert resp.status_code == 429

    # Advance clock beyond the window (oldest entry at t=0, window=60 s).
    # At t = 70 every entry satisfies: 70 - timestamp >= 60, so all are pruned.
    t[0] = 70.0
    resp = admin_client.post(
        f"/tickets/{customer_ticket.id}/ai/category-suggestion"
    )
    assert resp.status_code == 200, (
        "After the window expires the quota must reset and accept requests again"
    )


# ── Test 6: exhausted admin + nonexistent ticket → 404, not 429 ──────────────

def test_exhausted_quota_nonexistent_ticket_returns_404(
    admin_client, customer_ticket, monkeypatch
):
    """
    Error precedence: 403 (role) > 404 (ticket not found) > 429 (rate limit).

    Even after the admin's quota is exhausted, requesting a ticket that does
    not exist must return 404 — because the ticket lookup happens before the
    rate-limit check in the handler.
    """
    clock, t = _make_clock(0.0)
    monkeypatch.setattr("backend.tickets.routes.get_current_time", clock)
    monkeypatch.setattr("backend.tickets.routes.suggest_ticket_category", _fake_suggest)

    # Exhaust quota.
    for i in range(10):
        t[0] = float(i)
        resp = admin_client.post(
            f"/tickets/{customer_ticket.id}/ai/category-suggestion"
        )
        assert resp.status_code == 200

    # Confirm quota is exhausted for a known ticket.
    resp = admin_client.post(
        f"/tickets/{customer_ticket.id}/ai/category-suggestion"
    )
    assert resp.status_code == 429

    # Now request a ticket that does not exist — must be 404, not 429.
    resp = admin_client.post("/tickets/999999/ai/category-suggestion")
    assert resp.status_code == 404, (
        f"Expected 404 (ticket not found) before rate-limit check, got {resp.status_code}"
    )
