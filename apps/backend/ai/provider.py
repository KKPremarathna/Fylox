import json
import logging
from typing import Any
from backend.ai.schemas import BillingAnalysisResponse

logger = logging.getLogger(__name__)

def call_llm_provider(
    system_prompt: str,
    user_prompt: str,
    payment_evidence: dict[str, Any],
    policies: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Simulates calling an LLM provider to format findings securely.
    In a real implementation, this would use e.g., client.beta.chat.completions.parse
    For now, it returns a deterministic generated JSON string payload representing the LLM output.
    """
    # Deterministic Mock output based on input
    evidence_ids = payment_evidence.get('payment_ids', [])
    policy_ids = [p['id'] for p in policies]
    
    requires_review = False
    
    # If the user_prompt explicitly requests to trigger hallucination tests in mock
    if "HALLUCINATE_EVIDENCE" in user_prompt:
        evidence_ids = [9999]
    if "HALLUCINATE_POLICY" in user_prompt:
        policy_ids = [9999]
    if "REQUIRE_REVIEW" in user_prompt:
        requires_review = True

    return {
        "summary": "AI diagnosis: " + payment_evidence.get('message', 'No message'),
        "evidence_ids": evidence_ids,
        "policy_source_ids": policy_ids,
        "recommended_next_steps": ["Review transaction dashboard", "Consider refunding duplicate"],
        "reply_draft": f"Based on our review, {payment_evidence.get('message', '').lower()}",
        "requires_human_review": requires_review,
        "escalation_reason": "Escalated for testing" if requires_review else None
    }


def execute_billing_analysis(
    sanitized_payment_findings: dict[str, Any],
    matching_policies: list[dict[str, Any]],
    ticket_text: str
) -> dict[str, Any]:
    """
    Adapter wrapper handling timeouts and fallback behavior.
    """
    system_prompt = "You are a billing diagnostic assistant. Do not promise refunds, only explain evidence."
    user_prompt = f"Customer Query: {ticket_text}"
    
    if "FAIL_PROVIDER" in ticket_text:
        raise Exception("Simulated provider connection timeout")
        
    if "INVALID_JSON" in ticket_text:
        return {"garbage": "data"}

    return call_llm_provider(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        payment_evidence=sanitized_payment_findings,
        policies=matching_policies
    )

def generate_fallback_analysis(
    sanitized_payment_findings: dict[str, Any],
    fallback_reason: str
) -> dict[str, Any]:
    """
    Creates a deterministic safe fallback payload if provider fails.
    """
    evidence_ids = sanitized_payment_findings.get('payment_ids', [])
    return {
        "summary": "Fallback: System detected billing issue, AI unavailable.",
        "evidence_ids": evidence_ids,
        "policy_source_ids": [],
        "recommended_next_steps": ["Review payment intent dashboard manually."],
        "reply_draft": "I am looking into your billing concern.",
        "requires_human_review": True,
        "escalation_reason": "AI analysis was skipped or failed.",
        "analysis_source": "FALLBACK",
        "fallback_reason": fallback_reason
    }
