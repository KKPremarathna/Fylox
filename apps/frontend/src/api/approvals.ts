import type {
  ApprovalPaginatedResponse,
  ApprovalRequest,
  ApprovalStatus,
} from "../types/api";
import { apiRequest } from "./client";

export type CreateRefundReviewPayload = {
  ticket_id: number;
  reason: string;
};

export type EvaluateApprovalPayload = {
  status: ApprovalStatus;
  reviewer_note?: string;
};

export function createRefundReviewRequest(
  token: string,
  orderId: number,
  payload: CreateRefundReviewPayload,
): Promise<ApprovalRequest> {
  return apiRequest<ApprovalRequest>(
    `/orders/${orderId}/refund-review-requests`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    },
  );
}

export function getOrderRefundRequests(
  token: string,
  orderId: number,
): Promise<ApprovalRequest[]> {
  return apiRequest<ApprovalRequest[]>(
    `/orders/${orderId}/refund-review-requests`,
    {
      token,
    },
  );
}

export type AdminApprovalQueryParams = {
  status?: string;
  limit?: number;
  offset?: number;
};

export function getAdminApprovalRequests(
  token: string,
  params: AdminApprovalQueryParams = {},
): Promise<ApprovalPaginatedResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const queryString = query.toString();
  const path = `/admin/approval-requests${queryString ? `?${queryString}` : ""}`;

  return apiRequest<ApprovalPaginatedResponse>(path, {
    token,
  });
}

export function evaluateApprovalRequest(
  token: string,
  requestId: number,
  payload: EvaluateApprovalPayload,
): Promise<ApprovalRequest> {
  return apiRequest<ApprovalRequest>(
    `/admin/approval-requests/${requestId}`,
    {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    },
  );
}
