import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getOrders } from "../api/orders";
import { useAuth } from "../context/AuthContext";
import type { Order } from "../types/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function statusBadgeClass(status: Order["status"]) {
  switch (status) {
    case "PENDING":
      return "status-open";
    case "PROCESSING":
      return "status-in_progress";
    case "SHIPPED":
    case "DELIVERED":
      return "status-resolved";
    case "CANCELLED":
      return "status-closed";
    default:
      return "status-open";
  }
}

export function CustomerOrdersPage() {
  const { token } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    setIsLoading(true);
    setError(null);
    getOrders(token)
      .then((data) => {
        setOrders(data);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Unable to load your orders.",
        );
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [token]);

  return (
    <main className="dashboard-page">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">MY ACCOUNT</p>
          <h1>My Orders</h1>
          <p className="muted">
            View your purchase history and monitor payment details.
          </p>
        </div>
      </div>

      {isLoading && (
        <section className="empty-state" role="status">
          <p>Loading orders&hellip;</p>
        </section>
      )}

      {!isLoading && error && (
        <section className="form-error" role="alert">
          <strong>Error:</strong> {error}
        </section>
      )}

      {!isLoading && !error && orders.length === 0 && (
        <section className="empty-state" role="status">
          <h2>No orders found</h2>
          <p className="muted">You have not placed any orders yet.</p>
        </section>
      )}

      {!isLoading && !error && orders.length > 0 && (
        <div className="ticket-list" style={{ marginTop: "1.5rem" }}>
          {orders.map((order) => (
            <Link
              key={order.id}
              className="ticket-card ticket-card-link"
              to={`/orders/${order.id}`}
            >
              <div className="ticket-card-main">
                <div className="ticket-card-title">
                  <h3>Order #{order.order_number}</h3>
                  <span className={`status ${statusBadgeClass(order.status)}`}>
                    {order.status}
                  </span>
                </div>
                <p className="ticket-description">
                  Total: <strong>{order.currency} {order.total_amount}</strong>
                </p>
                <p className="ticket-date">
                  Placed on {formatDate(order.created_at)}
                </p>
              </div>
              <div className="ticket-card-meta">
                <span className="ticket-arrow" aria-hidden="true">
                  &rarr;
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
