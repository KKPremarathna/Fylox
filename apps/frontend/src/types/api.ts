export type UserRole = "ADMIN" | "CUSTOMER";

export type TicketStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "CLOSED";

export type TicketCategory =
  | "ACCOUNT_ACCESS"
  | "BILLING_PAYMENT"
  | "TECHNICAL_ISSUE"
  | "FEATURE_REQUEST"
  | "HOW_TO_SUPPORT"
  | "OTHER";

export type User = {
  user_id: number;
  username: string;
  email: string;
  role: UserRole;
  created_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
};

export type Ticket = {
  id: number;
  customer_id: number;
  assigned_admin_id: number | null;
  subject: string;
  description: string;
  status: TicketStatus;
  ai_suggested_category: TicketCategory | null;
  ai_category_confidence: number | null;
  final_category: TicketCategory | null;
  ai_category_approved: boolean | null;
  created_at: string;
  updated_at: string;
};

export type TicketMessage = {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_type: "CUSTOMER" | "ADMIN" | "AI";
  content: string;
  created_at: string;
};

export type TicketActivity = {
  id: number;
  ticket_id: number;
  actor_id: number | null;
  event_type: string;
  message: string;
  created_at: string;
};

/* --- Orders & Payments --- */

export type OrderStatus =
  | "PENDING"
  | "PROCESSING"
  | "SHIPPED"
  | "DELIVERED"
  | "CANCELLED";

export type Order = {
  id: number;
  order_number: string;
  customer_id: number;
  status: OrderStatus;
  total_amount: string;
  currency: string;
  created_at: string;
  updated_at: string;
};

export type DuplicateGroup = {
  amount: string;
  currency: string;
  payment_count: number;
};

export type DuplicateChargeCheckResponse = {
  order_id: number;
  has_possible_duplicate: boolean;
  successful_payment_count: number;
  duplicate_groups: DuplicateGroup[];
  message: string;
};

/* --- Approvals --- */

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export type SafeEvidenceJson = {
  rule_engine?: string;
  successful_payment_count?: number;
  duplicate_groups?: DuplicateGroup[];
};

export type ApprovalRequest = {
  id: number;
  ticket_id: number;
  order_id: number;
  request_type: string;
  status: ApprovalStatus;
  reason: string;
  evidence_json: SafeEvidenceJson;
  reviewer_note: string | null;
  created_at: string;
  reviewed_at: string | null;
  updated_at: string;
};

export type ApprovalPaginatedResponse = {
  items: ApprovalRequest[];
  total: number;
  limit: number;
  offset: number;
};

/* --- AI Router --- */

export type RoutingCategory = 
  | "ORDER_SUPPORT" 
  | "BILLING_SUPPORT" 
  | "POLICY_SUPPORT" 
  | "GENERAL_SUPPORT" 
  | "HUMAN_ESCALATION";

export type ClassifierType = "DETERMINISTIC" | "LLM" | "FALLBACK" | "SAFETY_GUARDRAIL";

export type RoutingDecision = {
  category: RoutingCategory;
  confidence: number;
  classifier_type: ClassifierType;
  escalation_reason?: string;
};

export type AIReplyResponse = {
  message_content: string | null;
  routing_decision: RoutingDecision;
  action_taken: string;
};