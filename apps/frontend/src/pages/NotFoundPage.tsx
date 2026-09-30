import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="page-center">
      <section className="auth-card">
        <h1>Page not found</h1>
        <p className="muted">
          The page you requested does not exist.
        </p>
        <Link to="/login">Go to sign in</Link>
      </section>
    </main>
  );
}