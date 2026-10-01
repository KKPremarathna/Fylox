import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const isAdmin = user?.role === "ADMIN";

  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink className="brand" to={isAdmin ? "/admin/tickets" : "/tickets"}>
          <span className="brand-mark">F</span>
          <span>Fylox</span>
        </NavLink>

        <nav aria-label="Main navigation" className="app-nav">
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to={isAdmin ? "/admin/tickets" : "/tickets"}
          >
            {isAdmin ? "Ticket queue" : "My tickets"}
          </NavLink>

          {!isAdmin && (
            <NavLink
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
              to="/orders"
            >
              My orders
            </NavLink>
          )}

          {isAdmin && (
            <>
              <NavLink
                className={({ isActive }) =>
                  isActive ? "nav-link nav-link-active" : "nav-link"
                }
                to="/admin/refund-queue"
              >
                Refund queue
              </NavLink>

              <NavLink
                className={({ isActive }) =>
                  isActive ? "nav-link nav-link-active" : "nav-link"
                }
                to="/admin/activity"
              >
                Activity history
              </NavLink>
            </>
          )}
        </nav>

        <div className="app-user-menu">
          <div className="app-user-details">
            <span className="app-user-name">{user?.username}</span>
            <span className="app-user-role">
              {isAdmin ? "Support admin" : "Customer"}
            </span>
          </div>

          <button
            className="theme-toggle-button"
            type="button"
            onClick={toggleTheme}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            aria-label="Toggle theme"
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>

          <button
            className="sign-out-button"
            type="button"
            onClick={logout}
          >
            Sign out
          </button>
        </div>
      </header>

      <Outlet />
    </div>
  );
}