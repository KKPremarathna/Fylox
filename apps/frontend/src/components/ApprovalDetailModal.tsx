import { useState } from "react";
import { evaluateApprovalRequest } from "../api/approvals";
import { useAuth } from "../context/AuthContext";
import type { ApprovalRequest } from "../types/api";

type ApprovalDetailModalProps = {
  request: ApprovalRequest | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function requestStatusBadgeClass(status: string) {
  switch (status) {
    case "PENDING":
      return "status-in_progress";
    case "APPROVED":
      return "status-resolved";
    case "REJECTED":
      return "status-closed";
    default:
      return "status-open";
  }
}

export function ApprovalDetailModal({
  request,
  isOpen,
  onClose,
  onSuccess,
}: ApprovalDetailModalProps) {
  const { token } = useAuth();
  const [reviewerNote, setReviewerNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !request) return null;

  const isPending = request.status === "PENDING";
  const isRejectDisabled = isSubmitting || reviewerNote.trim().length === 0;

  async function handleDecision(decisionStatus: "APPROVED" | "REJECTED") {
    if (!token || !request) return;

    if (decisionStatus === "REJECTED" && reviewerNote.trim().length === 0) {
      setError("A reviewer note is strictly required when rejecting a request.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await evaluateApprovalRequest(token, request.id, {
        status: decisionStatus,
        reviewer_note: reviewerNote.trim() || undefined,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while saving decision.",
      );
      // If 409 or another admin decided, trigger refresh after delay or user acknowledgement
      if (err instanceof Error && err.message.toLowerCase().includes("already")) {
        onSuccess();
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // Safe mapping of evidence fields only
  const evidence = request.evidence_json ?? {};
  const successfulCount = evidence.successful_payment_count;
  const dupGroups = evidence.duplicate_groups ?? [];

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card card" style={{ maxWidth: "36rem" }}>
        <header className="modal-header">
          <div>
            <p className="eyebrow">REFUND REVIEW REQUEST #{request.id}</p>
            <h2 className="modal-title">Review Request Details</h2>
          </div>
          <button
            className="modal-close-btn"
            type="button"
            onClick={onClose}
            aria-label="Close modal"
          >
            &times;
          </button>
        </header>

        {error && (
          <div className="form-error" role="alert" style={{ marginTop: "1rem" }}>
            {error}
          </div>
        )}

        <div className="modal-body">
          <div className="modal-info-grid">
            <div className="modal-info-card">
              <span className="crp-meta-label">Status</span>
              <div>
                <span className={`status ${requestStatusBadgeClass(request.status)}`}>
                  {request.status}
                </span>
              </div>
            </div>
            <div className="modal-info-card">
              <span className="crp-meta-label">Order ID</span>
              <p className="crp-category-value">#{request.order_id}</p>
            </div>
            <div className="modal-info-card">
              <span className="crp-meta-label">Ticket ID</span>
              <p className="crp-category-value">#{request.ticket_id}</p>
            </div>
          </div>

          <div className="modal-section">
            <span className="crp-meta-label">Customer Reason</span>
            <p className="modal-reason-text">{request.reason}</p>
          </div>

          {/* ── Mapped Safe Aggregate Evidence Only ── */}
          <div className="modal-evidence-card">
            <div className="evidence-header">
              <span className="crp-meta-label">Duplicate Payment Evidence</span>
            </div>
            {successfulCount !== undefined && (
              <p className="evidence-stat">
                Total Successful Payments: <strong>{successfulCount}</strong>
              </p>
            )}

            {dupGroups.length > 0 ? (
              <div className="evidence-matches">
                <span className="crp-meta-label">Matched Duplicate Amounts</span>
                <ul className="evidence-list">
                  {dupGroups.map((g, i) => (
                    <li key={i}>
                      {g.payment_count} payments of <strong>{g.currency} {g.amount}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="muted" style={{ fontSize: "0.85rem" }}>
                No duplicate payment groups logged in evidence summary.
              </p>
            )}
          </div>

          <div className="modal-section">
            <span className="crp-meta-label">Timeline</span>
            <p className="modal-timeline-text">
              Requested: {formatDate(request.created_at)}
              {request.reviewed_at && ` • Reviewed: ${formatDate(request.reviewed_at)}`}
            </p>
          </div>

          {request.reviewer_note && (
            <div className="modal-section">
              <span className="crp-meta-label">Reviewer Note</span>
              <p className="modal-reason-text">{request.reviewer_note}</p>
            </div>
          )}

          {/* ── Admin Decision Form ── */}
          {isPending && (
            <div className="modal-decision-form">
              <label htmlFor="admin-reviewer-note" className="filter-label">
                Reviewer Note <span style={{ color: "#e11d48" }}>* (required for rejection)</span>
              </label>
              <textarea
                id="admin-reviewer-note"
                className="modal-textarea"
                rows={3}
                placeholder="Enter admin review note or explanation..."
                value={reviewerNote}
                onChange={(e) => setReviewerNote(e.target.value)}
                disabled={isSubmitting}
              />

              <div className="modal-actions">
                <button
                  className="btn btn-secondary"
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-danger"
                  type="button"
                  disabled={isRejectDisabled}
                  onClick={() => void handleDecision("REJECTED")}
                >
                  {isSubmitting ? "Saving..." : "Reject"}
                </button>
                <button
                  className="btn btn-success"
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void handleDecision("APPROVED")}
                >
                  {isSubmitting ? "Saving..." : "Approve"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
