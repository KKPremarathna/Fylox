import type { DuplicateChargeCheckResponse, Order } from "../types/api";
import { apiRequest } from "./client";

export function getOrders(token: string): Promise<Order[]> {
  return apiRequest<Order[]>("/orders", {
    token,
  });
}

export function getOrder(token: string, orderId: number): Promise<Order> {
  return apiRequest<Order>(`/orders/${orderId}`, {
    token,
  });
}

export function getDuplicateChargeCheck(
  token: string,
  orderId: number,
): Promise<DuplicateChargeCheckResponse> {
  return apiRequest<DuplicateChargeCheckResponse>(
    `/orders/${orderId}/duplicate-charge-check`,
    {
      token,
    },
  );
}
