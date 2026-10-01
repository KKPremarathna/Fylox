from typing import TypedDict


class CategorySuggestion(TypedDict):
    suggested_category: str
    confidence: float
    reason: str
    source: str


def suggest_ticket_category(
    subject: str,
    description: str,
) -> CategorySuggestion:
    text = f"{subject}\n\n{description}".strip().lower()

    if not text:
        raise ValueError("Ticket text cannot be empty.")

    # Demo-only deterministic fallback classifier.
    if any(kw in text for kw in ["duplicate", "charge", "refund", "card", "payment"]):
        return {
            "suggested_category": "BILLING_PAYMENT",
            "confidence": 0.95,
            "reason": "Ticket mentions billing or payment keywords.",
            "source": "fallback",
        }

    if any(kw in text for kw in ["shipment", "tracking", "delivery", "arrived"]):
        return {
            "suggested_category": "ORDER_SUPPORT",
            "confidence": 0.90,
            "reason": "Ticket mentions shipping or delivery keywords.",
            "source": "fallback",
        }

    if any(kw in text for kw in ["password", "login", "account"]):
        return {
            "suggested_category": "ACCOUNT_SUPPORT",
            "confidence": 0.92,
            "reason": "Ticket mentions account access keywords.",
            "source": "fallback",
        }

    return {
        "suggested_category": "GENERAL_SUPPORT",
        "confidence": 0.85,
        "reason": "Default fallback for generic requests.",
        "source": "fallback",
    }