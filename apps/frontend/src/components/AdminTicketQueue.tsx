import { Link } from "react-router-dom";

import type { Ticket } from "../types/api";

type AdminTicketQueueProps = {
  tickets: Ticket[];
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
  onUpdateStatus,
}: AdminTicketQueueProps) {
  if (tickets.length === 0) {
    return (
      <section className="empty-state">
        <h2>No tickets in the queue</h2>
        <p>New customer tickets will appear here.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">SUPPORT QUEUE</p>
          <h2>All tickets</h2>
        </div>

        <span className="count-badge">{tickets.length}</span>
      </div>

      <div className="admin-ticket-list">
        {tickets.map((ticket) => (
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

              <label className="status-select-label">
                Update status
                <select
                  value={ticket.status}
                  onChange={(event) => {
                    void onUpdateStatus(
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
        ))}
      </div>
    </section>
  );
}