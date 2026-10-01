from sqlalchemy.orm import Session
from backend.policies.service import search_policies

# Do NOT import mutable billing scripts here to enforce boundary safely.
from backend.payments.service import check_duplicate_charges


def order_specialist(db: Session, message: str, customer_id: int) -> str:
    """
    Simulates handling order queries securely.
    """
    # In a real implementation this would fetch models and pass to LLM.
    # For now we simulate read-only retrieval logic constraint.
    return "Your order issue has been understood. (Automated Order Reply)"


def billing_specialist(db: Session, message: str, customer_id: int) -> str:
    """
    Acts exclusively on read-only billing paths. Generates NO mutant side-effects.
    Creates structured safe handoff replies.
    """
    # Cannot promise a refund under any criteria here.
    return "I see you have a billing concern. I cannot process refunds directly, but I have noted this. A support agent can review a formal request."


def policy_specialist(db: Session, message: str) -> str:
    """
    Passes message explicitly against RAG knowledge layer.
    """
    results = search_policies(db=db, query=message)
    if not results:
        return "I could not find a specific policy snippet for this query."
    
    top = results[0]
    return f"Based on the '{top.document_title}' policy: {top.snippet_text}"


def general_specialist(message: str) -> str:
    """
    Static polite redirection safely avoiding system tools entirely.
    """
    return "I'm a virtual assistant here to help. Could you provide more specific details?"


from backend.ai.schemas import RoutingCategory

def run_specialist_delegation(db: Session, category: RoutingCategory, message: str, customer_id: int) -> str | None:
    """
    Dispatches to isolated tools based precisely on routed category.
    """
    if category == RoutingCategory.ORDER_SUPPORT:
        return order_specialist(db, message, customer_id)
        
    elif category == RoutingCategory.POLICY_SUPPORT:
        return policy_specialist(db, message)
        
    elif category == RoutingCategory.GENERAL_SUPPORT:
        return general_specialist(message)
        
    # Billing Support and Human Escalation explicitly generate NO definitive AI reply payloads 
    # to avoid promising refunds/fixes while safely logging activity context.
    return None 
