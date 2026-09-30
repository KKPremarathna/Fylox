import { useAuth } from "../context/AuthContext";

export function AdminTicketsPage() {
  const { user, logout } = useAuth();

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">FYLOX ADMIN</p>
          <h1>Ticket queue</h1>
          <p className="muted">
            Signed in as {user?.username}.
          </p>
        </div>

        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>

      <section className="empty-state">
        <h2>Admin workspace is ready</h2>
        <p>
          Next, we will load, assign, and update tickets from the API.
        </p>
      </section>
    </main>
  );
}