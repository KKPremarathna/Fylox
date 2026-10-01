import { useEffect, useState } from "react";

import { createRefundReviewRequest } from "../api/approvals";
import { getTickets } from "../api/tickets";
import { useAuth } from "../context/AuthContext";
import type { Ticket } from "../types/api";

type RefundReviewModalProps = {
  orderId: number;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

export function RefundReviewModal({
  orderId,
  isOpen,
  onClose,
  onSuccess,
}: RefundReviewModalProps) {
  const { token } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string>("");
  const [reason, setReason] = useState("");
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !token) return;

    setIsLoadingTickets(true);
    setError(null);
    getTickets(token)
      .then((data) => {
        setTickets(data);
        if (data.length > 0) {
          setSelectedTicketId(String(data[0].id));
        }
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Unable to load support tickets.",
        );
      })
      .finally(() => {
        setIsLoadingTickets(false);
      });
  }, [isOpen, token]);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    if (!selectedTicketId) {
      setError("Please select a support ticket.");
      return;
    }

    if (!reason.trim()) {
      setError("Please describe the reason for your refund review request.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await createRefundReviewRequest(token, orderId, {
        ticket_id: Number(selectedTicketId),
        reason: reason.trim(),
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while submitting your request.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card card">
        <header className="modal-header">
          <h2 className="modal-title">Request Refund Review</h2>
          <button
            className="modal-close-btn"
            type="button"
            onClick={onClose}
            aria-label="Close modal"
          >
            &times;
          </button>
        </header>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}

          <div className="filter-group">
            <label htmlFor="modal-ticket-select" className="filter-label">
              Associated Support Ticket
            </label>
            {isLoadingTickets ? (
              <p className="muted">Loading support tickets...</p>
            ) : tickets.length === 0 ? (
              <p className="form-error">
                You do not have any open support tickets. Please create a ticket
                first to request a refund review.
              </p>
            ) : (
              <select
                id="modal-ticket-select"
                className="filter-select"
                value={selectedTicketId}
                onChange={(e) => setSelectedTicketId(e.target.value)}
                disabled={isSubmitting}
              >
                {tickets.map((ticket) => (
                  <option key={ticket.id} value={ticket.id}>
                    #{ticket.id} - {ticket.subject}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="filter-group" style={{ marginTop: "1rem" }}>
            <label htmlFor="modal-reason" className="filter-label">
              Reason for Review Request
            </label>
            <textarea
              id="modal-reason"
              className="filter-input"
              rows={4}
              placeholder="Provide details about the duplicate charge (e.g. charged twice on card)..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="modal-actions" style={{ marginTop: "1.5rem" }}>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={isSubmitting || tickets.length === 0}
            >
              {isSubmitting ? "Submitting..." : "Submit Request"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
