import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "./components/AdminRoute";
import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminTicketsPage } from "./pages/AdminTicketsPage";
import { AdminActivityHistoryPage } from "./pages/AdminActivityHistoryPage";
import { AdminRefundQueuePage } from "./pages/AdminRefundQueuePage";
import { CustomerTicketsPage } from "./pages/CustomerTicketsPage";
import { CustomerOrdersPage } from "./pages/CustomerOrdersPage";
import { CustomerOrderDetailPage } from "./pages/CustomerOrderDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/tickets" element={<CustomerTicketsPage />} />
          <Route
            path="/tickets/:ticketId"
            element={<TicketDetailPage />}
          />
          <Route path="/orders" element={<CustomerOrdersPage />} />
          <Route
            path="/orders/:orderId"
            element={<CustomerOrderDetailPage />}
          />

          <Route element={<AdminRoute />}>
            <Route
              path="/admin/tickets"
              element={<AdminTicketsPage />}
            />
            <Route
              path="/admin/refund-queue"
              element={<AdminRefundQueuePage />}
            />
            <Route
              path="/admin/activity"
              element={<AdminActivityHistoryPage />}
            />
          </Route>
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default App;