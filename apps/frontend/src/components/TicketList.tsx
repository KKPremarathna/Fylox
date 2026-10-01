import { Link } from "react-router-dom";

import type { Ticket } from "../types/api";

type TicketListProps = {
  tickets: Ticket[];
  filterElement?: React.ReactNode;
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
  filterElement,
}: TicketListProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div className="panel-heading-main">
          <p className="eyebrow">MY SUPPORT REQUESTS</p>
          <div className="panel-title-row">
            <h2>Tickets</h2>
            <span className="count-badge">{tickets.length}</span>
          </div>
        </div>

        {filterElement ? (
          <div className="panel-heading-actions">{filterElement}</div>
        ) : null}
      </div>

      {tickets.length === 0 ? (
        <div className="empty-state-inner">
          <p className="muted">No tickets found matching this criteria.</p>
        </div>
      ) : (
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
      )}
    </section>
  );
}