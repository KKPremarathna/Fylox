import type { Ticket } from "../types/api";
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