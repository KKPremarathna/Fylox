import { useCallback, useEffect, useState } from "react";

import {
  getAdminTickets,
  updateAdminTicket,
} from "../api/tickets";
import { AdminTicketQueue } from "../components/AdminTicketQueue";
import { useAuth } from "../context/AuthContext";
import type { Ticket } from "../types/api";

export function AdminTicketsPage() {
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
      const result = await getAdminTickets(token);
      setTickets(result);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to load the ticket queue.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  async function applyTicketUpdate(
    ticketId: number,
    payload: {
      assigned_admin_id?: number | null;
      status?: Ticket["status"];
    },
  ) {
    if (!token) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const updatedTicket = await updateAdminTicket(
      token,
      ticketId,
      payload,
    );

    setTickets((currentTickets) =>
      currentTickets.map((ticket) =>
        ticket.id === updatedTicket.id
          ? updatedTicket
          : ticket,
      ),
    );
  }

  async function handleClaimTicket(ticketId: number) {
    if (!user) {
      throw new Error("Your account details are unavailable.");
    }

    await applyTicketUpdate(ticketId, {
      assigned_admin_id: user.user_id,
    });
  }

  async function handleUpdateStatus(
    ticketId: number,
    status: Ticket["status"],
  ) {
    await applyTicketUpdate(ticketId, { status });
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">FYLOX ADMIN</p>
          <h1>Ticket queue</h1>
          <p className="muted">
            Signed in as {user?.username}. Review, claim, and resolve
            customer support requests.
          </p>
        </div>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

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
        <section className="empty-state" role="status">
          <p>Loading the ticket queue...</p>
        </section>
      ) : (
        <AdminTicketQueue
          tickets={tickets}
          currentAdminId={user?.user_id}
          onClaimTicket={handleClaimTicket}
          onUpdateStatus={handleUpdateStatus}
        />
      )}
    </main>
  );
}