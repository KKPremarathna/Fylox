import { useState } from "react";
import { Link } from "react-router-dom";

import type { Ticket } from "../types/api";

type AdminTicketQueueProps = {
  tickets: Ticket[];
  currentAdminId: number | undefined;
  filterElement?: React.ReactNode;
  onClaimTicket: (ticketId: number) => Promise<void>;
  onUpdateStatus: (
    ticketId: number,
    status: Ticket["status"],
  ) => Promise<void>;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: Ticket["status"]) {
  return status.replace("_", " ");
}

export function AdminTicketQueue({
  tickets,
  currentAdminId,
  filterElement,
  onClaimTicket,
  onUpdateStatus,
}: AdminTicketQueueProps) {
  const [updatingTicketId, setUpdatingTicketId] = useState<number | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  async function handleClaimTicket(ticketId: number) {
    setError(null);
    setUpdatingTicketId(ticketId);

    try {
      await onClaimTicket(ticketId);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to claim this ticket.",
      );
    } finally {
      setUpdatingTicketId(null);
    }
  }

  async function handleStatusChange(
    ticketId: number,
    status: Ticket["status"],
  ) {
    setError(null);
    setUpdatingTicketId(ticketId);

    try {
      await onUpdateStatus(ticketId, status);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to update ticket status.",
      );
    } finally {
      setUpdatingTicketId(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div className="panel-heading-main">
          <p className="eyebrow">SUPPORT QUEUE</p>
          <div className="panel-title-row">
            <h2>All tickets</h2>
            <span className="count-badge">{tickets.length}</span>
          </div>
        </div>

        {filterElement ? (
          <div className="panel-heading-actions">{filterElement}</div>
        ) : null}
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      {tickets.length === 0 ? (
        <div className="empty-state-inner">
          <p className="muted">No tickets found in the queue.</p>
        </div>
      ) : (
        <div className="admin-ticket-list">
        {tickets.map((ticket) => {
          const isUpdating = updatingTicketId === ticket.id;
          const isClaimedByCurrentAdmin =
            ticket.assigned_admin_id === currentAdminId;

          return (
            <article className="admin-ticket-card" key={ticket.id}>
              <div className="admin-ticket-content">
                <div className="ticket-card-title">
                  <span className="ticket-id">#{ticket.id}</span>
                  <h3>{ticket.subject}</h3>
                </div>

                <p className="ticket-description">
                  {ticket.description}
                </p>

                <div className="admin-ticket-details">
                  <span>
                    Customer ID: {ticket.customer_id}
                  </span>
                  <span>
                    Assigned admin:{" "}
                    {ticket.assigned_admin_id ?? "Unassigned"}
                  </span>
                  <span>
                    Created {formatDate(ticket.created_at)}
                  </span>
                </div>
              </div>

              <div className="admin-ticket-actions">
                <span
                  className={`status status-${ticket.status.toLowerCase()}`}
                >
                  {statusLabel(ticket.status)}
                </span>

                <button
                  className="secondary-button"
                  type="button"
                  disabled={isUpdating || isClaimedByCurrentAdmin}
                  onClick={() => void handleClaimTicket(ticket.id)}
                >
                  {isClaimedByCurrentAdmin
                    ? "Claimed by you"
                    : "Claim ticket"}
                </button>

                <label className="status-select-label">
                  Update status
                  <select
                    disabled={isUpdating}
                    value={ticket.status}
                    onChange={(event) => {
                      void handleStatusChange(
                        ticket.id,
                        event.target.value as Ticket["status"],
                      );
                    }}
                  >
                    <option value="OPEN">Open</option>
                    <option value="IN_PROGRESS">
                      In progress
                    </option>
                    <option value="RESOLVED">Resolved</option>
                    <option value="CLOSED">Closed</option>
                  </select>
                </label>

                <Link
                  className="view-ticket-link"
                  to={`/tickets/${ticket.id}`}
                >
                  Open ticket →
                </Link>
              </div>
            </article>
          );
        })}
      </div>
      )}
    </section>
  );
}