import { useCallback, useEffect, useRef, useState } from "react";

import {
  type AdminActivityHistoryResponse,
  type AdminActivityItem,
  getAdminActivity,
} from "../api/activity";
import { useAuth } from "../context/AuthContext";

const PAGE_LIMIT = 20;

const EVENT_TYPE_OPTIONS = [
  "TICKET_CREATED",
  "TICKET_ASSIGNED",
  "TICKET_UNASSIGNED",
  "TICKET_RESOLVED",
  "TICKET_CLOSED",
  "STATUS_CHANGED",
  "AI_CATEGORY_SUGGESTED",
  "AI_CATEGORY_ACCEPTED",
  "AI_CATEGORY_REVIEWED",
  "CATEGORY_MANUALLY_SET",
  "REFUND_REVIEW_REQUESTED",
  "REFUND_REVIEW_APPROVED",
  "REFUND_REVIEW_REJECTED",
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function AdminActivityHistoryPage() {
  const { token } = useAuth();

  // Filter state
  const [ticketIdInput, setTicketIdInput] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [startDateFilter, setStartDateFilter] = useState("");
  const [endDateFilter, setEndDateFilter] = useState("");

  // Pagination
  const [offset, setOffset] = useState(0);

  // Data state
  const [data, setData] = useState<AdminActivityHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stable ref for abort controller
  const abortRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    if (!token) return;

    // Cancel any in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const result = await getAdminActivity(token, {
        ticket_id: ticketIdInput ? Number(ticketIdInput) : undefined,
        event_type: eventTypeFilter || undefined,
        start_date: startDateFilter || undefined,
        end_date: endDateFilter || undefined,
        limit: PAGE_LIMIT,
        offset,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token, ticketIdInput, eventTypeFilter, startDateFilter, endDateFilter, offset]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Reset to page 0 when filters change (except offset itself)
  function applyFilters() {
    setOffset(0);
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_LIMIT) : 0;
  const currentPage = Math.floor(offset / PAGE_LIMIT) + 1;
  const hasPrev = offset > 0;
  const hasNext = data ? offset + PAGE_LIMIT < data.total : false;

  return (
    <main className="admin-activity-page page-container">
      <div className="page-header">
        <h1 className="page-title">Activity History</h1>
        <p className="page-subtitle">
          Browse all system events across every support ticket.
        </p>
      </div>

      {/* ── Filter bar ── */}
      <section
        aria-label="Activity filters"
        className="activity-filters card"
      >
        <div className="filter-row">
          <div className="filter-group">
            <label className="filter-label" htmlFor="filter-ticket-id">
              Ticket ID
            </label>
            <input
              className="filter-input"
              id="filter-ticket-id"
              min={1}
              placeholder="e.g. 42"
              type="number"
              value={ticketIdInput}
              onChange={(e) => setTicketIdInput(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label className="filter-label" htmlFor="filter-event-type">
              Event type
            </label>
            <select
              className="filter-select"
              id="filter-event-type"
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
            >
              <option value="">All events</option>
              {EVENT_TYPE_OPTIONS.map((et) => (
                <option key={et} value={et}>
                  {et.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label" htmlFor="filter-start-date">
              From
            </label>
            <input
              className="filter-input"
              id="filter-start-date"
              type="datetime-local"
              value={startDateFilter}
              onChange={(e) => setStartDateFilter(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label className="filter-label" htmlFor="filter-end-date">
              To
            </label>
            <input
              className="filter-input"
              id="filter-end-date"
              type="datetime-local"
              value={endDateFilter}
              onChange={(e) => setEndDateFilter(e.target.value)}
            />
          </div>

          <button
            className="btn btn-primary"
            type="button"
            onClick={applyFilters}
          >
            Apply
          </button>

          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => {
              setTicketIdInput("");
              setEventTypeFilter("");
              setStartDateFilter("");
              setEndDateFilter("");
              setOffset(0);
            }}
          >
            Clear
          </button>
        </div>
      </section>

      {/* ── States ── */}
      {loading && (
        <div className="state-message" role="status">
          Loading activity&hellip;
        </div>
      )}

      {!loading && error && (
        <div className="state-message state-error" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <div className="state-message state-empty" role="status">
          No activity records match your filters.
        </div>
      )}

      {/* ── Results table ── */}
      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="table-wrapper">
            <table className="activity-table" aria-label="Activity records">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Ticket</th>
                  <th scope="col">Event</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Message</th>
                  <th scope="col">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item: AdminActivityItem) => (
                  <tr key={item.id}>
                    <td className="cell-id">{item.id}</td>
                    <td>
                      <div className="ticket-cell">
                        <span className="ticket-id-badge">#{item.ticket_id}</span>
                        <span className="ticket-subject">{item.ticket_subject}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`event-badge event-badge-${item.event_type.toLowerCase()}`}>
                        {item.event_type.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="cell-actor">
                      {item.actor_username ?? (
                        <span className="text-muted">System</span>
                      )}
                    </td>
                    <td className="cell-message">{item.message}</td>
                    <td className="cell-timestamp">
                      <time dateTime={item.created_at}>
                        {formatDate(item.created_at)}
                      </time>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Pagination ── */}
          <nav
            aria-label="Activity history pagination"
            className="pagination-bar"
          >
            <button
              aria-disabled={!hasPrev}
              className="btn btn-ghost pagination-btn"
              disabled={!hasPrev}
              id="activity-prev-page"
              type="button"
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_LIMIT))}
            >
              ← Previous
            </button>

            <span className="pagination-info" aria-live="polite">
              Page {currentPage} of {totalPages || 1} &mdash;{" "}
              {data.total} total record{data.total !== 1 ? "s" : ""}
            </span>

            <button
              aria-disabled={!hasNext}
              className="btn btn-ghost pagination-btn"
              disabled={!hasNext}
              id="activity-next-page"
              type="button"
              onClick={() => setOffset((o) => o + PAGE_LIMIT)}
            >
              Next →
            </button>
          </nav>
        </>
      )}
    </main>
  );
}
