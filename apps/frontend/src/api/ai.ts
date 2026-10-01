import { apiRequest } from "./client";
import type { AIReplyResponse } from "../types/api";

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
