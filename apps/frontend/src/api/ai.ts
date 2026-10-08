import { apiRequest } from "./client";
import type { AIReplyResponse, BillingAnalysisResponse } from "../types/api";

export async function generateTicketAiReply(
  token: string,
  ticketId: number,
  message: string,
): Promise<AIReplyResponse> {
  return apiRequest<AIReplyResponse>(`/ai/tickets/${ticketId}/ai-reply`, {
    method: "POST",
    token,
    body: JSON.stringify({ message }),
  });
}

export async function generateBillingAnalysis(
  token: string,
  ticketId: number,
  orderId: number,
): Promise<BillingAnalysisResponse> {
  return apiRequest<BillingAnalysisResponse>(`/ai/tickets/${ticketId}/billing-analysis`, {
    method: "POST",
    token,
    body: JSON.stringify({ order_id: orderId }),
  });
}
