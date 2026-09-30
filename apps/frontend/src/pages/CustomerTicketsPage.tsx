import { useCallback, useEffect, useState } from "react";

import { createTicket, getTickets } from "../api/tickets";
import { CreateTicketForm } from "../components/CreateTicketForm";
import { TicketList } from "../components/TicketList";
import { useAuth } from "../context/AuthContext";
import type { Ticket } from "../types/api";

export function CustomerTicketsPage() {
  const { user, token, logout } = useAuth();

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTickets = useCallback(async () => {
    if (!token) {
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const result = await getTickets(token);
      setTickets(result);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to load tickets.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  async function handleCreateTicket(
    subject: string,
    description: string,
  ) {
    if (!token) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const newTicket = await createTicket(token, {
      subject,
      description,
    });

    setTickets((currentTickets) => [
      newTicket,
      ...currentTickets,
    ]);
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">FYLOX SUPPORT</p>
          <h1>My tickets</h1>
          <p className="muted">
            Welcome back, {user?.username}. Create and track your
            support requests here.
          </p>
        </div>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

      <CreateTicketForm onSubmit={handleCreateTicket} />

      {error ? (
        <section className="form-error" role="alert">
          {error}
          <button
            className="retry-button"
            type="button"
            onClick={() => void loadTickets()}
          >
            Retry
          </button>
        </section>
      ) : null}

      {isLoading ? (
        <section className="empty-state">
          <p>Loading your tickets...</p>
        </section>
      ) : (
        <TicketList tickets={tickets} />
      )}
    </main>
  );
}