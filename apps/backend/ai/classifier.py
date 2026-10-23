import re

from backend.ai.schemas import (
    ClassifierType,
    RoutingCategory,
    RoutingDecision,
)


INJECTION_PATTERNS = (
    "ignore previous instructions",
    "you are now a",
    "system prompt",
    "forget all rules",
)


def normalize_message(message: str) -> str:
    return " ".join(message.casefold().split())


def detect_injection(message: str) -> bool:
    """
    Basic phrase-based guardrail.

    This is not comprehensive prompt-injection detection.
    """
    normalized = normalize_message(message)

    return any(
        pattern in normalized
        for pattern in INJECTION_PATTERNS
    )


def matches(pattern: str, message: str) -> bool:
    return re.search(pattern, message) is not None


def run_deterministic_fast_path(
    message: str,
) -> tuple[RoutingCategory | None, float]:
    """
    Apply ordered routing rules.

    Scores are fixed routing heuristics, not calibrated
    probabilities of correctness.
    """
    normalized = normalize_message(message)

    if not normalized:
        return None, 0.0

    # Explicit human-contact requests and legal concerns.
    human_request = matches(
        r"\b(?:speak|talk|connect|transfer|escalate)"
        r"\s+(?:me\s+)?(?:directly\s+)?"
        r"(?:(?:to|with)\s+)?(?:a\s+|an\s+)?"
        r"(?:human|agent|operator|representative)\b",
        normalized,
    )

    human_request = human_request or matches(
        r"\b(?:i\s+)?(?:want|need)"
        r"\s+(?:a\s+|an\s+)?"
        r"(?:human|agent|operator|representative)\b",
        normalized,
    )

    if (
        human_request
        or normalized in {
            "human",
            "agent",
            "operator",
            "representative",
            "human agent",
        }
        or matches(
            r"\b(?:sue you|lawsuit|lawyer)\b",
            normalized,
        )
    ):
        return RoutingCategory.HUMAN_ESCALATION, 1.0

    # Route policy questions before generic refund keywords.
    policy_question = matches(
        r"\b(?:policy|policies|return window|guarantee)\b",
        normalized,
    )

    billing_action = matches(
        r"\b(?:"
        r"(?:i\s+)?(?:want|need|request)"
        r"\s+(?:a\s+)?refund"
        r"|refund\s+(?:me|my\s+payment)"
        r"|money back"
        r"|charged twice"
        r"|billed twice"
        r"|duplicate\s+(?:charge|payment)"
        r")\b",
        normalized,
    )

    if policy_question and not billing_action:
        return RoutingCategory.POLICY_SUPPORT, 0.90

    if matches(
        r"\b(?:"
        r"charge|charged|charges"
        r"|refund|refunds"
        r"|duplicate"
        r"|billed twice|charged twice"
        r"|money back"
        r"|billing"
        r"|payment|payments"
        r")\b",
        normalized,
    ):
        return RoutingCategory.BILLING_SUPPORT, 0.95

    if matches(
        r"\b(?:"
        r"shipping"
        r"|tracking(?: code| number)?"
        r"|where is my package"
        r"|order status"
        r"|shipment"
        r"|cancel (?:my |the )?order"
        r")\b",
        normalized,
    ):
        return RoutingCategory.ORDER_SUPPORT, 0.95

    if matches(
        r"\border\s*#\s*[a-z0-9]"
        r"|\border\s+(?:number|no\.?)\s*[:#]?\s*[a-z0-9]",
        normalized,
    ):
        return RoutingCategory.ORDER_SUPPORT, 0.95

    if normalized in {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
        "help",
        "help me",
    }:
        return RoutingCategory.GENERAL_SUPPORT, 0.90

    return None, 0.0


def classify_message(message: str) -> RoutingDecision:
    """
    Route using phrase guardrails and deterministic rules.

    No external LLM is called.
    """
    normalized = normalize_message(message)

    if not normalized:
        return RoutingDecision(
            category=RoutingCategory.GENERAL_SUPPORT,
            confidence=0.0,
            classifier_type=ClassifierType.FALLBACK,
            escalation_reason=None,
        )

    if detect_injection(normalized):
        return RoutingDecision(
            category=RoutingCategory.HUMAN_ESCALATION,
            confidence=1.0,
            classifier_type=ClassifierType.SAFETY_GUARDRAIL,
            escalation_reason=(
                "Prompt-injection phrase heuristic matched; "
                "human review is required."
            ),
        )

    category, score = run_deterministic_fast_path(normalized)

    if category is not None:
        return RoutingDecision(
            category=category,
            confidence=score,
            classifier_type=ClassifierType.DETERMINISTIC,
            escalation_reason=(
                "Explicit human-contact or legal-concern "
                "routing rule matched."
                if category == RoutingCategory.HUMAN_ESCALATION
                else None
            ),
        )

    return RoutingDecision(
        category=RoutingCategory.HUMAN_ESCALATION,
        confidence=0.0,
        classifier_type=ClassifierType.FALLBACK,
        escalation_reason=(
            "No supported deterministic routing rule matched; "
            "human review is required."
        ),
    )