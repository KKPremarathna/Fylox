import type { TicketActivity } from "../types/api";

type ActivityTimelineProps = {
  activity: TicketActivity[];
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function eventTypeBadge(eventType: string) {
  switch (eventType) {
    case "REFUND_REVIEW_REQUESTED":
      return <span className="status status-in_progress">Refund Review Requested</span>;
    case "REFUND_REVIEW_APPROVED":
      return <span className="status status-resolved">Refund Review Approved</span>;
    case "REFUND_REVIEW_REJECTED":
      return <span className="status status-closed">Refund Review Rejected</span>;
    case "AI_ROUTED":
      return <span className="status status-open">Routed by AI</span>;
    default:
      return null;
  }
}

function processActivityMessage(item: TicketActivity) {
  if (item.event_type !== "AI_ROUTED") {
    return <p style={{ marginTop: item.event_type.startsWith("REFUND_REVIEW") ? "0.35rem" : "0" }}>{item.message}</p>;
  }

  try {
    const meta = JSON.parse(item.message);
    const pct = meta.confidence ? (meta.confidence * 100).toFixed(0) + "%" : "N/A";
    return (
      <div style={{ marginTop: "0.5rem", padding: "0.75rem", backgroundColor: "#f9fafb", borderRadius: "0.25rem", border: "1px solid #e5e7eb" }}>
        <strong>AI Triage Details:</strong>
        <ul style={{ margin: "0.25rem 0 0 0", paddingLeft: "1.25rem", fontSize: "0.875rem", color: "#4b5563" }}>
          <li>Category: {meta.category}</li>
          <li>Classifier: {meta.classifier_type}</li>
          <li>Confidence: {pct}</li>
          {meta.escalation_reason && <li>Note: {meta.escalation_reason}</li>}
        </ul>
      </div>
    );
  } catch (e) {
    return <p>{item.message}</p>;
  }
}


export function ActivityTimeline({ activity }: ActivityTimelineProps) {
  if (activity.length === 0) {
    return (
      <p className="muted">
        No activity has been recorded for this ticket yet.
      </p>
    );
  }

  return (
    <ol className="activity-timeline">
      {activity.map((item) => (
        <li key={item.id}>
          <span className="activity-dot" aria-hidden="true" />
          <div>
            {eventTypeBadge(item.event_type)}
            {processActivityMessage(item)}
            <time dateTime={item.created_at}>
              {formatDate(item.created_at)}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}