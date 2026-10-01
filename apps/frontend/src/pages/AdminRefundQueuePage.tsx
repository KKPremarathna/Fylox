import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  type AdminApprovalQueryParams,
  getAdminApprovalRequests,
} from "../api/approvals";
import { ApprovalDetailModal } from "../components/ApprovalDetailModal";
import { useAuth } from "../context/AuthContext";
import type { ApprovalPaginatedResponse, ApprovalRequest } from "../types/api";

const PAGE_LIMIT = 20;

const STATUS_FILTER_OPTIONS = [
  { label: "Pending Review", value: "PENDING" },
  { label: "Approved", value: "APPROVED" },
  { label: "Rejected", value: "REJECTED" },
  { label: "All Requests", value: "" },
];

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

export function AdminRefundQueuePage() {
  const { token } = useAuth();

  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [offset, setOffset] = useState(0);

  const [data, setData] = useState<ApprovalPaginatedResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    if (!token) return;

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      const params: AdminApprovalQueryParams = {
        status: statusFilter || undefined,
        limit: PAGE_LIMIT,
        offset,
      };

      const result = await getAdminApprovalRequests(token, params);
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load refund review requests.",
      );
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [token, statusFilter, offset]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const totalPages = data ? Math.ceil(data.total / PAGE_LIMIT) : 0;
  const currentPage = Math.floor(offset / PAGE_LIMIT) + 1;
  const hasPrev = offset > 0;
  const hasNext = data ? offset + PAGE_LIMIT < data.total : false;

  function handleOpenModal(req: ApprovalRequest) {
    setSelectedRequest(req);
    setIsModalOpen(true);
  }

  return (
    <main className="admin-activity-page page-container">
      <div className="page-header">
        <h1 className="page-title">Refund Review Queue</h1>
        <p className="page-subtitle">
          Manage and decide customer refund review requests for potential duplicate charges.
        </p>
      </div>

      {/* ── Filter bar ── */}
      <section
        aria-label="Approval request filters"
        className="ticket-filters card"
        style={{ marginBottom: "1.5rem" }}
      >
        {STATUS_FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={
              statusFilter === opt.value
                ? "filter-button filter-button-active"
                : "filter-button"
            }
            type="button"
            onClick={() => {
              setStatusFilter(opt.value);
              setOffset(0);
            }}
          >
            {opt.label}
          </button>
        ))}
      </section>

      {/* ── States ── */}
      {isLoading && (
        <div className="state-message" role="status">
          Loading approval requests&hellip;
        </div>
      )}

      {!isLoading && error && (
        <div className="state-message state-error" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!isLoading && !error && data && data.items.length === 0 && (
        <div className="state-message state-empty" role="status">
          No refund review requests match the selected status filter.
        </div>
      )}

      {/* ── Results table ── */}
      {!isLoading && !error && data && data.items.length > 0 && (
        <>
          <div className="table-wrapper">
            <table
              className="activity-table"
              aria-label="Refund review request queue"
            >
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Order ID</th>
                  <th scope="col">Ticket ID</th>
                  <th scope="col">Status</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Requested At</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td className="cell-id">#{item.id}</td>
                    <td>
                      <Link to={`/orders/${item.order_id}`}>
                        #{item.order_id}
                      </Link>
                    </td>
                    <td>
                      <Link to={`/tickets/${item.ticket_id}`}>
                        #{item.ticket_id}
                      </Link>
                    </td>
                    <td>
                      <span
                        className={`status ${requestStatusBadgeClass(item.status)}`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="cell-message">{item.reason}</td>
                    <td className="cell-timestamp">
                      <time dateTime={item.created_at}>
                        {formatDate(item.created_at)}
                      </time>
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost"
                        style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}
                        type="button"
                        onClick={() => handleOpenModal(item)}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Pagination ── */}
          <nav
            aria-label="Refund queue pagination"
            className="pagination-bar"
            style={{ marginTop: "1rem" }}
          >
            <button
              aria-disabled={!hasPrev}
              className="btn btn-ghost pagination-btn"
              disabled={!hasPrev}
              type="button"
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_LIMIT))}
            >
              &larr; Previous
            </button>

            <span className="pagination-info" aria-live="polite">
              Page {currentPage} of {totalPages || 1} &mdash; {data.total} total request{data.total !== 1 ? "s" : ""}
            </span>

            <button
              aria-disabled={!hasNext}
              className="btn btn-ghost pagination-btn"
              disabled={!hasNext}
              type="button"
              onClick={() => setOffset((o) => o + PAGE_LIMIT)}
            >
              Next &rarr;
            </button>
          </nav>
        </>
      )}

      {/* ── Detail Modal ── */}
      <ApprovalDetailModal
        request={selectedRequest}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => void fetchData()}
      />
    </main>
  );
}
