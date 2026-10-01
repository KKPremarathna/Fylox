import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getOrderRefundRequests } from "../api/approvals";
import { getDuplicateChargeCheck, getOrder } from "../api/orders";
import { RefundReviewModal } from "../components/RefundReviewModal";
import { useAuth } from "../context/AuthContext";
import type {
  ApprovalRequest,
  DuplicateChargeCheckResponse,
  Order,
} from "../types/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function requestStatusBadgeClass(status: string) {
  switch (status) {
    case "PENDING":
      return "status-in_progress";
    case "APPROVED":
      return "status-resolved";
    case "REJECTED":
      return "status-closed";
    default:
      return "status-open";
  }
}

export function CustomerOrderDetailPage() {
  const { orderId } = useParams();
  const { token } = useAuth();
  const numericOrderId = Number(orderId);

  const [order, setOrder] = useState<Order | null>(null);
  const [duplicateCheck, setDuplicateCheck] =
    useState<DuplicateChargeCheckResponse | null>(null);
  const [refundRequests, setRefundRequests] = useState<ApprovalRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    if (!token || !Number.isInteger(numericOrderId)) {
      setError("Invalid order ID.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [orderRes, dupRes, requestsRes] = await Promise.all([
        getOrder(token, numericOrderId),
        getDuplicateChargeCheck(token, numericOrderId),
        getOrderRefundRequests(token, numericOrderId),
      ]);

      setOrder(orderRes);
      setDuplicateCheck(dupRes);
      setRefundRequests(requestsRes);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load order details.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [token, numericOrderId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  if (isLoading) {
    return (
      <main className="dashboard-page">
        <section className="empty-state" role="status">
          <p>Loading order details&hellip;</p>
        </section>
      </main>
    );
  }

  if (error || !order) {
    return (
      <main className="dashboard-page">
        <Link className="back-link" to="/orders">
          &larr; Back to orders
        </Link>
        <section className="form-error" role="alert">
          {error ?? "Order not found."}
        </section>
      </main>
    );
  }

  const activePendingRequest = refundRequests.find(
    (req) => req.status === "PENDING",
  );

  return (
    <main className="dashboard-page">
      <Link className="back-link" to="/orders">
        &larr; Back to orders
      </Link>

      <header className="ticket-detail-header">
        <div>
          <p className="eyebrow">ORDER #{order.order_number}</p>
          <h1>Order Summary</h1>
          <p className="muted">Placed on {formatDate(order.created_at)}</p>
        </div>
        <span className="status status-open">{order.status}</span>
      </header>

      {/* ── Order summary card ── */}
      <section className="panel">
        <div className="panel-heading">
          <h2>Financial Details</h2>
        </div>
        <p>
          Total Amount: <strong>{order.currency} {order.total_amount}</strong>
        </p>
      </section>

      {/* ── Duplicate Charge Check Alert Banner & Actions ── */}
      {duplicateCheck && duplicateCheck.has_possible_duplicate && (
        <section
          className="panel"
          style={{
            borderColor: "#f59e0b",
            background: "#fffbe8",
          }}
        >
          <div className="panel-heading">
            <div>
              <p className="eyebrow" style={{ color: "#d97706" }}>
                DUPLICATE CHARGE DETECTED
              </p>
              <h2 style={{ color: "#92400e" }}>Possible Double Charge Found</h2>
            </div>
          </div>
          <p style={{ color: "#78350f" }}>{duplicateCheck.message}</p>

          {duplicateCheck.duplicate_groups.length > 0 && (
            <ul style={{ margin: "0.5rem 0 1rem 1.25rem", color: "#78350f" }}>
              {duplicateCheck.duplicate_groups.map((group, idx) => (
                <li key={idx}>
                  {group.payment_count} successful payments of{" "}
                  <strong>
                    {group.currency} {group.amount}
                  </strong>
                </li>
              ))}
            </ul>
          )}

          {activePendingRequest ? (
            <div
              style={{
                marginTop: "1rem",
                padding: "0.75rem 1rem",
                borderRadius: "0.5rem",
                background: "#fef3c7",
                border: "1px solid #fde68a",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.75rem",
              }}
            >
              <span className="status status-in_progress">
                PENDING REVIEW
              </span>
              <span style={{ fontSize: "0.9rem", color: "#92400e" }}>
                A refund review request submitted on{" "}
                {formatDate(activePendingRequest.created_at)} is currently under review by our support team.
              </span>
            </div>
          ) : (
            <div style={{ marginTop: "1rem" }}>
              <button
                className="btn btn-primary"
                type="button"
                onClick={() => setIsModalOpen(true)}
              >
                Request Refund Review
              </button>
            </div>
          )}
        </section>
      )}

      {/* ── Refund Review Requests History ── */}
      <section className="panel" style={{ marginTop: "2rem" }}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">WORKFLOW HISTORY</p>
            <h2>Refund Review Requests</h2>
          </div>
        </div>

        {refundRequests.length === 0 ? (
          <p className="muted">
            No refund review requests have been submitted for this order.
          </p>
        ) : (
          <div className="table-wrapper">
            <table
              className="activity-table"
              aria-label="Refund review request history"
            >
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Ticket ID</th>
                  <th scope="col">Status</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Requested At</th>
                  <th scope="col">Reviewed At</th>
                  <th scope="col">Reviewer Note</th>
                </tr>
              </thead>
              <tbody>
                {refundRequests.map((req) => (
                  <tr key={req.id}>
                    <td className="cell-id">#{req.id}</td>
                    <td>
                      <Link to={`/tickets/${req.ticket_id}`}>
                        #{req.ticket_id}
                      </Link>
                    </td>
                    <td>
                      <span
                        className={`status ${requestStatusBadgeClass(req.status)}`}
                      >
                        {req.status}
                      </span>
                    </td>
                    <td className="cell-message">{req.reason}</td>
                    <td className="cell-timestamp">
                      <time dateTime={req.created_at}>
                        {formatDate(req.created_at)}
                      </time>
                    </td>
                    <td className="cell-timestamp">
                      {req.reviewed_at ? (
                        <time dateTime={req.reviewed_at}>
                          {formatDate(req.reviewed_at)}
                        </time>
                      ) : (
                        <span className="text-muted">&mdash;</span>
                      )}
                    </td>
                    <td className="cell-message">
                      {req.reviewer_note ?? (
                        <span className="text-muted">&mdash;</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Request Modal ── */}
      <RefundReviewModal
        orderId={order.id}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => void loadData()}
      />
    </main>
  );
}
