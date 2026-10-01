import re
from backend.ai.schemas import RoutingCategory, RoutingDecision, ClassifierType


def detect_injection(message: str) -> bool:
    """
    Very basic heuristic injection pattern detection.
    Looks for prompt hijacking instructions.
    """
    lower = message.lower()
    dangerous_patterns = [
        "ignore previous instructions",
        "you are now a",
        "system prompt",
        "forget all rules",
    ]
    return any(p in lower for p in dangerous_patterns)


def run_deterministic_fast_path(message: str) -> tuple[RoutingCategory | None, float]:
    """
    Evaluates message deterministically against strict keywords for fast pathing.
    Returns (Category, confidence) if a highly confident match is found.
    """
    lower = message.lower()
    
    # Check for direct escalation intents
    if re.search(r'\b(sue you|lawsuit|lawyer|human|agent|operator)\b', lower):
        return RoutingCategory.HUMAN_ESCALATION, 1.0
        
    # Check Billing rules
    if re.search(r'\b(charge|refund|duplicate|billed twice|money back)\b', lower):
        return RoutingCategory.BILLING_SUPPORT, 0.95
        
    # Check Order rules
    if re.search(r'\b(shipping|tracking code|where is my package|order status|shipment)\b', lower):
        return RoutingCategory.ORDER_SUPPORT, 0.95
        
    # Check Policy rules
    if re.search(r'\b(what is your policy|return window|guarantee)\b', lower):
        return RoutingCategory.POLICY_SUPPORT, 0.90
        
    return None, 0.0


def run_mock_llm_adapter(message: str) -> tuple[RoutingCategory, float]:
    """
    A stand-in for an external LLM classification call (e.g. OpenAI).
    In this capstone slice, we mock behavior behind this clean boundary.
    """
    # Simple simulated processing boundary
    # Because LLM acts as fallback, if it reaches here and we don't have a clear mapping,
    # it's usually safest to hand off to human or general.
    if len(message.split()) < 3:
        # Probable small talk "Hi", "Hello"
        return RoutingCategory.GENERAL_SUPPORT, 0.85
        
    return RoutingCategory.HUMAN_ESCALATION, 0.60


def classify_message(message: str) -> RoutingDecision:
    """
    The main routing orchestrator.
    Determines safety, fast-paths securely, and falls back gracefully.
    """
    if detect_injection(message):
        return RoutingDecision(
            category=RoutingCategory.HUMAN_ESCALATION,
            confidence=1.0,
            classifier_type=ClassifierType.SAFETY_GUARDRAIL,
            escalation_reason="Prompt injection heuristic identified"
        )
        
    cat, conf = run_deterministic_fast_path(message)
    if cat is not None and conf > 0.8:
        return RoutingDecision(
            category=cat,
            confidence=conf,
            classifier_type=ClassifierType.DETERMINISTIC
        )
        
    llm_cat, llm_conf = run_mock_llm_adapter(message)
    if llm_conf < 0.7:
         return RoutingDecision(
            category=RoutingCategory.HUMAN_ESCALATION,
            confidence=llm_conf,
            classifier_type=ClassifierType.FALLBACK,
            escalation_reason="Low LLM confidence"
        )
         
    return RoutingDecision(
        category=llm_cat,
        confidence=llm_conf,
        classifier_type=ClassifierType.LLM
    )
