import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  acceptAiCategorySuggestion,
  createTicketMessage,
  getTicket,
  getTicketActivity,
  getTicketMessages,
  requestAiCategorySuggestion,
  reviewTicketCategory,
} from "../api/tickets";
import { ActivityTimeline } from "../components/ActivityTimeline";
import { Conversation } from "../components/Conversation";
import { MessageForm } from "../components/MessageForm";
import { useAuth } from "../context/AuthContext";
import { generateTicketAiReply, generateBillingAnalysis } from "../api/ai";
import type {
  Ticket,
  TicketActivity,
  TicketCategory,
  TicketMessage,
  BillingAnalysisResponse,
} from "../types/api";


const ticketCategories: TicketCategory[] = [
  "ACCOUNT_SUPPORT",
  "BILLING_PAYMENT",
  "ORDER_SUPPORT",
  "TECHNICAL_ISSUE",
  "FEATURE_REQUEST",
  "HOW_TO_SUPPORT",
  "GENERAL_SUPPORT",
  "OTHER",
];


function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


function formatConfidence(value: number | null) {
  if (value === null) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}


function statusLabel(status: Ticket["status"]) {
  return status.replace("_", " ");
}


function categoryLabel(category: TicketCategory) {
  return category.replaceAll("_", " ");
}


export function TicketDetailPage() {
  const { ticketId } = useParams();
  const { token, user } = useAuth();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [messages, setMessages] = useState<TicketMessage[]>([]);
  const [activity, setActivity] = useState<TicketActivity[]>([]);
  const [selectedCategory, setSelectedCategory] =
    useState<TicketCategory>("OTHER");
  const [isLoading, setIsLoading] = useState(true);
  const [isCategoryActionLoading, setIsCategoryActionLoading] =
    useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [aiAnalysisDetails, setAiAnalysisDetails] = useState<{ reason?: string; source?: string } | null>(null);

  // Billing Analysis State
  const [orderIdStr, setOrderIdStr] = useState("");
  const [billingAnalysis, setBillingAnalysis] = useState<BillingAnalysisResponse | null>(null);
  const [isBillingAnalysisLoading, setIsBillingAnalysisLoading] = useState(false);
  const [billingAnalysisError, setBillingAnalysisError] = useState<string | null>(null);

  const numericTicketId = Number(ticketId);

  const backPath =
    user?.role === "ADMIN"
      ? "/admin/tickets"
      : "/tickets";

  const backLabel =
    user?.role === "ADMIN"
      ? "← Back to admin queue"
      : "← Back to tickets";

  const isAdmin = user?.role === "ADMIN";

  async function handleGenerateBillingAnalysis() {
    if (!token || !Number.isInteger(numericTicketId)) return;
    const orderId = Number(orderIdStr);
    if (!Number.isInteger(orderId) || orderId <= 0) {
      setBillingAnalysisError("Please enter a valid positive Order ID.");
      return;
    }
    
    setBillingAnalysisError(null);
    setIsBillingAnalysisLoading(true);
    setBillingAnalysis(null);

    try {
      const resp = await generateBillingAnalysis(token, numericTicketId, orderId);
      setBillingAnalysis(resp);
      await refreshTicketAndActivity();
    } catch (caughtError) {
      setBillingAnalysisError(
        caughtError instanceof Error ? caughtError.message : "Unable to generate billing analysis."
      );
    } finally {
      setIsBillingAnalysisLoading(false);
    }
  }

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
      setSelectedCategory(
        ticketResult.final_category
          ?? ticketResult.ai_suggested_category
          ?? "OTHER",
      );
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

  async function refreshTicketAndActivity() {
    if (!token || !Number.isInteger(numericTicketId)) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const [updatedTicket, updatedActivity] = await Promise.all([
      getTicket(token, numericTicketId),
      getTicketActivity(token, numericTicketId),
    ]);

    setTicket(updatedTicket);
    setActivity(updatedActivity);
    setSelectedCategory(
      updatedTicket.final_category
        ?? updatedTicket.ai_suggested_category
        ?? "OTHER",
    );
  }

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

  async function handleAiMessage(content: string) {
    if (!token || !Number.isInteger(numericTicketId)) {
      throw new Error("Your session has expired. Please sign in again.");
    }
    
    // Calls the AI layer
    await generateTicketAiReply(
      token,
      numericTicketId,
      content,
    );

    // Refresh everything directly after AI execution (safe messages are implicitly written)
    const [updatedMessages, updatedActivity] = await Promise.all([
      getTicketMessages(token, numericTicketId),
      getTicketActivity(token, numericTicketId),
    ]);

    setMessages(updatedMessages);
    setActivity(updatedActivity);
  }

  async function handleGetAiSuggestion() {
    if (!token || !Number.isInteger(numericTicketId)) {
      return;
    }

    setCategoryError(null);
    setIsCategoryActionLoading(true);

    try {
      const resp = await requestAiCategorySuggestion(token, numericTicketId);
      setAiAnalysisDetails({ reason: resp.reason, source: resp.source });
      await refreshTicketAndActivity();
    } catch (caughtError) {
      setCategoryError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to get an AI category suggestion.",
      );
    } finally {
      setIsCategoryActionLoading(false);
    }
  }

  async function handleAcceptAiSuggestion() {
    if (!token || !Number.isInteger(numericTicketId)) {
      return;
    }

    setCategoryError(null);
    setIsCategoryActionLoading(true);

    try {
      await acceptAiCategorySuggestion(token, numericTicketId);
      await refreshTicketAndActivity();
    } catch (caughtError) {
      setCategoryError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to accept the AI category suggestion.",
      );
    } finally {
      setIsCategoryActionLoading(false);
    }
  }

  async function handleSaveCategory() {
    if (!token || !Number.isInteger(numericTicketId)) {
      return;
    }

    setCategoryError(null);
    setIsCategoryActionLoading(true);

    try {
      await reviewTicketCategory(
        token,
        numericTicketId,
        selectedCategory,
      );
      await refreshTicketAndActivity();
    } catch (caughtError) {
      setCategoryError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to save the ticket category.",
      );
    } finally {
      setIsCategoryActionLoading(false);
    }
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
        <Link className="back-link" to={backPath}>
          {backLabel}
        </Link>

        <section className="form-error" role="alert">
          {error ?? "Ticket not found."}
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard-page">
      <Link className="back-link" to={backPath}>
        {backLabel}
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

      {isAdmin ? (
        <section className="panel category-review-panel">
          {/* ── Panel header band ── */}
          <div className="crp-header">
            <div className="crp-header-text">
              <p className="eyebrow">AI-ASSISTED TRIAGE</p>
              <h2 className="crp-title">Category Review</h2>
            </div>
            <span className="crp-badge">
              {ticket.ai_suggested_category ? "✦ Suggestion ready" : "Awaiting analysis"}
            </span>
          </div>

          {/* ── AI suggestion block ── */}
          {ticket.ai_suggested_category ? (
            <div className="crp-suggestion-block">
              <div className="crp-suggestion-meta">
                <div>
                  <p className="crp-meta-label">AI Suggestion</p>
                  <p className="crp-category-value">
                    {categoryLabel(ticket.ai_suggested_category)}
                  </p>
                </div>
                <div className="crp-confidence">
                  <p className="crp-meta-label">Model confidence</p>
                  <div className="crp-confidence-row">
                    <div className="crp-confidence-bar-track">
                      <div
                        className="crp-confidence-bar-fill"
                        style={{
                          width: ticket.ai_category_confidence != null
                            ? `${(ticket.ai_category_confidence * 100).toFixed(1)}%`
                            : "0%",
                        }}
                      />
                    </div>
                    <span className="crp-confidence-pct">
                      {formatConfidence(ticket.ai_category_confidence)}
                    </span>
                  </div>
                </div>
              </div>

              {aiAnalysisDetails?.reason && (
                <div className="crp-ai-details-box" style={{ marginTop: "1rem", fontSize: "0.9rem", color: "#666" }}>
                  <p><strong>Reason:</strong> {aiAnalysisDetails.reason}</p>
                  {aiAnalysisDetails.source && <p><strong>Source:</strong> {aiAnalysisDetails.source}</p>}
                </div>
              )}

              <button
                className="crp-accept-btn"
                type="button"
                disabled={isCategoryActionLoading}
                onClick={() => void handleAcceptAiSuggestion()}
              >
                {isCategoryActionLoading ? "Saving…" : "✔ Accept AI suggestion"}
              </button>
            </div>
          ) : (
            <div className="crp-empty-block">
              <div className="crp-empty-icon">🤖</div>
              <p className="crp-empty-text">
                No AI suggestion has been requested yet for this ticket.
              </p>
              <button
                className="crp-ai-btn"
                type="button"
                disabled={isCategoryActionLoading}
                onClick={() => void handleGetAiSuggestion()}
              >
                {isCategoryActionLoading ? "Analysing…" : "✦ Get AI suggestion"}
              </button>
            </div>
          )}

          {/* ── Manual override ── */}
          <div className="crp-manual-row">
            <label className="crp-manual-label" htmlFor="final-category">
              Final category
            </label>
            <div className="crp-manual-controls">
              <select
                id="final-category"
                className="crp-select"
                value={selectedCategory}
                disabled={isCategoryActionLoading}
                onChange={(event) =>
                  setSelectedCategory(event.target.value as TicketCategory)
                }
              >
                {ticketCategories.map((category) => (
                  <option key={category} value={category}>
                    {categoryLabel(category)}
                  </option>
                ))}
              </select>

              <button
                className="primary-button crp-save-btn"
                type="button"
                disabled={isCategoryActionLoading}
                onClick={() => void handleSaveCategory()}
              >
                {isCategoryActionLoading ? "Saving…" : "Save category"}
              </button>
            </div>
          </div>

          {/* ── Saved state chip ── */}
          {ticket.final_category ? (
            <div className="crp-saved-state">
              <span className="crp-saved-chip">
                ✔ Current: {categoryLabel(ticket.final_category)}
                {ticket.ai_category_approved === true && " · AI-approved"}
                {ticket.ai_category_approved === false && " · Manually overridden"}
              </span>
            </div>
          ) : null}

          {categoryError ? (
            <p className="form-error" role="alert">
              {categoryError}
            </p>
          ) : null}
        </section>
      ) : null}

      {isAdmin ? (
        <section className="panel billing-analysis-panel" style={{ marginTop: "1.5rem" }}>
          <div className="crp-header">
            <div className="crp-header-text">
              <p className="eyebrow">BILLING DIAGNOSTICS</p>
              <h2 className="crp-title">AI Billing Analysis</h2>
            </div>
            <span className="crp-badge">
              {billingAnalysis ? "✦ Analysis ready" : "Awaiting order"}
            </span>
          </div>

          <div className="crp-manual-row" style={{ marginTop: "1rem" }}>
            <label className="crp-manual-label" htmlFor="order-id">
              Order ID
            </label>
            <div className="crp-manual-controls">
              <input
                id="order-id"
                type="number"
                placeholder="e.g. 1"
                className="crp-select"
                value={orderIdStr}
                disabled={isBillingAnalysisLoading}
                onChange={(e) => setOrderIdStr(e.target.value)}
              />
              <button
                className="primary-button crp-save-btn"
                type="button"
                disabled={isBillingAnalysisLoading}
                onClick={() => void handleGenerateBillingAnalysis()}
              >
                {isBillingAnalysisLoading ? "Analysing…" : "Generate Analysis"}
              </button>
            </div>
          </div>

          {billingAnalysisError ? (
            <p className="form-error" role="alert" style={{ marginTop: "1rem" }}>
              {billingAnalysisError}
            </p>
          ) : null}

          {billingAnalysis ? (
            <div className="crp-suggestion-block" style={{ marginTop: "1rem", outline: billingAnalysis.requires_human_review ? '2px solid orange' : 'none' }}>
              <div style={{ marginBottom: "1rem" }}>
                <p className="crp-meta-label">Summary</p>
                <p style={{ fontWeight: 'bold' }}>{billingAnalysis.summary}</p>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <p className="crp-meta-label">Recommended Next Steps</p>
                <ul style={{ paddingLeft: "1.5rem", fontSize: "0.9rem" }}>
                  {billingAnalysis.recommended_next_steps.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ul>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <p className="crp-meta-label">Suggested Reply Draft</p>
                <blockquote style={{ borderLeft: "4px solid #e5e7eb", paddingLeft: "1rem", fontStyle: "italic", margin: "0.5rem 0", color: "#4b5563" }}>
                  {billingAnalysis.reply_draft}
                </blockquote>
              </div>

              <div style={{ fontSize: "0.85rem", color: "#666", display: "flex", gap: "1rem", flexWrap: "wrap", backgroundColor: "#f9fafb", padding: "0.75rem", borderRadius: "0.25rem" }}>
                <span><strong>Source:</strong> {billingAnalysis.analysis_source}</span>
                {billingAnalysis.fallback_reason && <span><strong>Fallback Reason:</strong> {billingAnalysis.fallback_reason}</span>}
                {billingAnalysis.escalation_reason && <span style={{ color: "orange" }}><strong>Escalation:</strong> {billingAnalysis.escalation_reason}</span>}
                <span><strong>Evidence IDs:</strong> {billingAnalysis.evidence_ids.join(", ") || "None"}</span>
                <span><strong>Policy IDs:</strong> {billingAnalysis.policy_source_ids.join(", ") || "None"}</span>
                <span><strong>Requires Review:</strong> {billingAnalysis.requires_human_review ? "Yes" : "No"}</span>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}


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

          <MessageForm onSubmit={handleSendMessage} onAiSubmit={handleAiMessage} />
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