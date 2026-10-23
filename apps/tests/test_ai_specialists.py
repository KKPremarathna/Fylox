import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps"))

from backend.ai import specialists
from backend.ai.schemas import RoutingCategory


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "Check order #FY-1001",
            {"FY-1001"},
        ),
        (
            "Where is order number FY-1001?",
            {"FY-1001"},
        ),
        (
            "Check order no: FY-1001",
            {"FY-1001"},
        ),
        (
            "Check payment 101",
            set(),
        ),
        (
            "Where is my package?",
            set(),
        ),
    ],
)
def test_extract_order_numbers(message, expected):
    assert (
        specialists.extract_order_numbers(message)
        == expected
    )


def test_missing_reference_does_not_query_database():
    db = Mock()

    reply = specialists.order_specialist(
        db=db,
        message="Where is my package?",
        customer_id=7,
    )

    db.scalars.assert_not_called()
    assert "provide your order number" in reply.lower()


def test_multiple_references_require_clarification():
    db = Mock()

    reply = specialists.order_specialist(
        db=db,
        message="Check order #FY-1001 and order #FY-1002",
        customer_id=7,
    )

    db.scalars.assert_not_called()
    assert "one order number at a time" in reply


def test_order_query_contains_customer_and_order_filters():
    db = Mock()
    db.scalars.return_value.one_or_none.return_value = None

    specialists.order_specialist(
        db=db,
        message="Check order #FY-1001",
        customer_id=7,
    )

    statement = db.scalars.call_args.args[0]
    compiled = statement.compile()
    sql = str(compiled)

    assert "orders.customer_id =" in sql
    assert "orders.order_number =" in sql
    assert 7 in compiled.params.values()
    assert "FY-1001" in compiled.params.values()


def test_missing_order_returns_generic_customer_scoped_reply():
    db = Mock()
    db.scalars.return_value.one_or_none.return_value = None

    reply = specialists.order_specialist(
        db=db,
        message="Check order #FY-1001",
        customer_id=7,
    )

    assert "could not find that order" in reply
    assert "linked to this ticket" in reply


def test_order_reply_uses_stored_status():
    db = Mock()
    db.scalars.return_value.one_or_none.return_value = (
        SimpleNamespace(
            order_number="FY-1001",
            status="SHIPPED",
        )
    )

    reply = specialists.order_specialist(
        db=db,
        message="Check order #FY-1001",
        customer_id=7,
    )

    assert "#FY-1001" in reply
    assert "SHIPPED" in reply
    assert "does not include carrier tracking" in reply

    db.commit.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "category",
    [
        RoutingCategory.BILLING_SUPPORT,
        RoutingCategory.HUMAN_ESCALATION,
    ],
)
def test_sensitive_categories_do_not_generate_auto_replies(
    category,
):
    db = Mock()

    reply = specialists.run_specialist_delegation(
        db=db,
        category=category,
        message="Please review this concern.",
        customer_id=7,
    )

    assert reply is None
    db.scalars.assert_not_called()
    db.commit.assert_not_called()


def test_policy_without_matches_requests_details(monkeypatch):
    monkeypatch.setattr(
        specialists,
        "search_policies",
        Mock(return_value=[]),
    )

    reply = specialists.policy_specialist(
        db=Mock(),
        message="What is your guarantee?",
    )

    assert "could not find a matching" in reply


def test_policy_reply_includes_source_and_limit(monkeypatch):
    result = SimpleNamespace(
        document_title="Returns Policy",
        chunk_id=201,
        snippet_text="Eligible returns require review.",
    )

    monkeypatch.setattr(
        specialists,
        "search_policies",
        Mock(return_value=[result]),
    )

    reply = specialists.policy_specialist(
        db=Mock(),
        message="What is your return window?",
    )

    assert "Returns Policy" in reply
    assert "201" in reply
    assert result.snippet_text in reply
    assert "does not confirm eligibility" in reply