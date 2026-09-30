import { apiRequest } from "./client";

export type AdminActivityItem = {
  id: number;
  ticket_id: number;
  ticket_subject: string;
  actor_id: number | null;
  actor_username: string | null;
  event_type: string;
  message: string;
  created_at: string;
};

export type AdminActivityHistoryResponse = {
  items: AdminActivityItem[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminActivityFilters = {
  ticket_id?: number;
  event_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
};

export function getAdminActivity(
  token: string,
  filters: AdminActivityFilters = {},
): Promise<AdminActivityHistoryResponse> {
  const params = new URLSearchParams();

  if (filters.ticket_id !== undefined) {
    params.set("ticket_id", String(filters.ticket_id));
  }
  if (filters.event_type) {
    params.set("event_type", filters.event_type);
  }
  if (filters.start_date) {
    params.set("start_date", filters.start_date);
  }
  if (filters.end_date) {
    params.set("end_date", filters.end_date);
  }
  if (filters.limit !== undefined) {
    params.set("limit", String(filters.limit));
  }
  if (filters.offset !== undefined) {
    params.set("offset", String(filters.offset));
  }

  const qs = params.toString();

  return apiRequest<AdminActivityHistoryResponse>(
    `/admin/activity${qs ? `?${qs}` : ""}`,
    { token },
  );
}
