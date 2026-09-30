import type {
  Ticket,
  TicketActivity,
  TicketMessage,
  TicketStatus,
} from "../types/api";
import { apiRequest } from "./client";

type CreateTicketPayload = {
  subject: string;
  description: string;
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

export type AdminTicketUpdate = {
  assigned_admin_id?: number | null;
  status?: TicketStatus;
};

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