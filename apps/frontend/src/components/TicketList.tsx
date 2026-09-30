import { Link } from "react-router-dom";

import type { Ticket } from "../types/api";

type TicketListProps = {
  tickets: Ticket[];
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

export function TicketList({
  tickets,
}: TicketListProps) {
  if (tickets.length === 0) {
    return (
      <section className="empty-state">
        <h2>No tickets yet</h2>
        <p>
          Create your first support ticket using the form above.
        </p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">MY SUPPORT REQUESTS</p>
          <h2>Tickets</h2>
        </div>

        <span className="count-badge">{tickets.length}</span>
      </div>

      <div className="ticket-list">
        {tickets.map((ticket) => (
          <Link
            className="ticket-card ticket-card-link"
            key={ticket.id}
            to={`/tickets/${ticket.id}`}
          >
            <div className="ticket-card-main">
              <div className="ticket-card-title">
                <span className="ticket-id">#{ticket.id}</span>
                <h3>{ticket.subject}</h3>
              </div>

              <p className="ticket-description">
                {ticket.description}
              </p>

              <p className="ticket-date">
                Created {formatDate(ticket.created_at)}
              </p>
            </div>

            <div className="ticket-card-meta">
              <span
                className={`status status-${ticket.status.toLowerCase()}`}
              >
                {statusLabel(ticket.status)}
              </span>

              <span className="ticket-arrow" aria-hidden="true">
                →
              </span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}