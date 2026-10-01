import type {
  Ticket,
  TicketActivity,
  TicketCategory,
  TicketMessage,
  TicketStatus,
} from "../types/api";
import { apiRequest } from "./client";


type CreateTicketPayload = {
  subject: string;
  description: string;
};


export type AdminTicketUpdate = {
  assigned_admin_id?: number | null;
  status?: TicketStatus;
};


export type TicketCategorySuggestion = {
  ticket_id: number;
  suggested_category: TicketCategory;
  confidence: number;
  reason?: string;
  source?: string;
};


export function getTickets(token: string): Promise<Ticket[]> {
  return apiRequest<Ticket[]>("/tickets", {
    token,
  });
}


export function getTicket(
  token: string,
  ticketId: number,
): Promise<Ticket> {
  return apiRequest<Ticket>(`/tickets/${ticketId}`, {
    token,
  });
}


export function createTicket(
  token: string,
  payload: CreateTicketPayload,
): Promise<Ticket> {
  return apiRequest<Ticket>("/tickets", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}


export function getTicketMessages(
  token: string,
  ticketId: number,
): Promise<TicketMessage[]> {
  return apiRequest<TicketMessage[]>(
    `/tickets/${ticketId}/messages`,
    {
      token,
    },
  );
}


export function createTicketMessage(
  token: string,
  ticketId: number,
  content: string,
): Promise<TicketMessage> {
  return apiRequest<TicketMessage>(
    `/tickets/${ticketId}/messages`,
    {
      method: "POST",
      token,
      body: JSON.stringify({ content }),
    },
  );
}


export function getTicketActivity(
  token: string,
  ticketId: number,
): Promise<TicketActivity[]> {
  return apiRequest<TicketActivity[]>(
    `/tickets/${ticketId}/activity`,
    {
      token,
    },
  );
}


export function getAdminTickets(
  token: string,
): Promise<Ticket[]> {
  return apiRequest<Ticket[]>("/admin/tickets", {
    token,
  });
}


export function updateAdminTicket(
  token: string,
  ticketId: number,
  payload: AdminTicketUpdate,
): Promise<Ticket> {
  return apiRequest<Ticket>(
    `/admin/tickets/${ticketId}`,
    {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    },
  );
}


export function requestAiCategorySuggestion(
  token: string,
  ticketId: number,
): Promise<TicketCategorySuggestion> {
  return apiRequest<TicketCategorySuggestion>(
    `/tickets/${ticketId}/ai/category-suggestion`,
    {
      method: "POST",
      token,
    },
  );
}


export function acceptAiCategorySuggestion(
  token: string,
  ticketId: number,
): Promise<Ticket> {
  return apiRequest<Ticket>(
    `/tickets/${ticketId}/accept-ai-category`,
    {
      method: "PATCH",
      token,
    },
  );
}


export function reviewTicketCategory(
  token: string,
  ticketId: number,
  finalCategory: TicketCategory,
): Promise<Ticket> {
  return apiRequest<Ticket>(
    `/tickets/${ticketId}/category-review`,
    {
      method: "PATCH",
      token,
      body: JSON.stringify({
        final_category: finalCategory,
      }),
    },
  );
}