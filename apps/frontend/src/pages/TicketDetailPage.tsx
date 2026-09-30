import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  createTicketMessage,
  getTicket,
  getTicketActivity,
  getTicketMessages,
} from "../api/tickets";
import { ActivityTimeline } from "../components/ActivityTimeline";
import { Conversation } from "../components/Conversation";
import { MessageForm } from "../components/MessageForm";
import { useAuth } from "../context/AuthContext";
import type {
  Ticket,
  TicketActivity,
  TicketMessage,
} from "../types/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: Ticket["status"]) {
  return status.replace("_", " ");
}

export function TicketDetailPage() {
  const { ticketId } = useParams();
  const { token, user } = useAuth();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [messages, setMessages] = useState<TicketMessage[]>([]);
  const [activity, setActivity] = useState<TicketActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const numericTicketId = Number(ticketId);

  const loadTicketData = useCallback(async () => {
    if (!token || !Number.isInteger(numericTicketId)) {
      setError("Invalid ticket ID.");
      setIsLoading(false);
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const [ticketResult, messagesResult, activityResult] =
        await Promise.all([
          getTicket(token, numericTicketId),
          getTicketMessages(token, numericTicketId),
          getTicketActivity(token, numericTicketId),
        ]);

      setTicket(ticketResult);
      setMessages(messagesResult);
      setActivity(activityResult);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to load this ticket.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [token, numericTicketId]);

  useEffect(() => {
    void loadTicketData();
  }, [loadTicketData]);

  async function handleSendMessage(content: string) {
    if (!token || !Number.isInteger(numericTicketId)) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const newMessage = await createTicketMessage(
      token,
      numericTicketId,
      content,
    );

    setMessages((currentMessages) => [
      ...currentMessages,
      newMessage,
    ]);

    const updatedActivity = await getTicketActivity(
      token,
      numericTicketId,
    );

    setActivity(updatedActivity);
  }

  if (isLoading) {
    return (
      <main className="dashboard-page">
        <section className="empty-state">
          <p>Loading ticket...</p>
        </section>
      </main>
    );
  }

  if (error || !ticket) {
    return (
      <main className="dashboard-page">
        <Link className="back-link" to="/tickets">
          ← Back to tickets
        </Link>

        <section className="form-error" role="alert">
          {error ?? "Ticket not found."}
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard-page">
      <Link className="back-link" to="/tickets">
        ← Back to tickets
      </Link>

      <header className="ticket-detail-header">
        <div>
          <p className="eyebrow">TICKET #{ticket.id}</p>
          <h1>{ticket.subject}</h1>
          <p className="muted">
            Created {formatDate(ticket.created_at)}
          </p>
        </div>

        <span
          className={`status status-${ticket.status.toLowerCase()}`}
        >
          {statusLabel(ticket.status)}
        </span>
      </header>

      <section className="panel ticket-summary">
        <h2>Original request</h2>
        <p>{ticket.description}</p>
      </section>

      <div className="ticket-detail-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">CONVERSATION</p>
              <h2>Messages</h2>
            </div>
          </div>

          <Conversation
            messages={messages}
            currentUserId={user?.user_id}
          />

          <MessageForm onSubmit={handleSendMessage} />
        </section>

        <aside className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">HISTORY</p>
              <h2>Activity</h2>
            </div>
          </div>

          <ActivityTimeline activity={activity} />
        </aside>
      </div>
    </main>
  );
}