import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function AdminRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <main className="page-center">
        <p>Loading your session...</p>
      </main>
    );
  }

  if (!user || user.role !== "ADMIN") {
    return <Navigate to="/tickets" replace />;
  }

  return <Outlet />;
}