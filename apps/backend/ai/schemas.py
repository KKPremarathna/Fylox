from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RoutingCategory(str, Enum):
    ORDER_SUPPORT = "ORDER_SUPPORT"
    BILLING_SUPPORT = "BILLING_SUPPORT"
    POLICY_SUPPORT = "POLICY_SUPPORT"
    GENERAL_SUPPORT = "GENERAL_SUPPORT"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class ClassifierType(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LLM = "LLM"
    FALLBACK = "FALLBACK"
    SAFETY_GUARDRAIL = "SAFETY_GUARDRAIL"


class ClassifyRequest(BaseModel):
    message: str


class RoutingDecision(BaseModel):
    category: RoutingCategory
    confidence: float
    classifier_type: ClassifierType
    escalation_reason: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AIReplyResponse(BaseModel):
    message_content: Optional[str]
    routing_decision: RoutingDecision
    action_taken: str


class BillingAnalysisRequest(BaseModel):
    order_id: int


class BillingAnalysisResponse(BaseModel):
    id: int
    ticket_id: int
    order_id: int
    admin_id: Optional[int]
    
    summary: str
    evidence_ids: list[int] 
    policy_source_ids: list[int]
    recommended_next_steps: list[str]
    reply_draft: str
    
    requires_human_review: bool
    escalation_reason: Optional[str] = None
    analysis_source: str
    fallback_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
