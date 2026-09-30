export type UserRole = "ADMIN" | "CUSTOMER";

export type TicketStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "CLOSED";

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