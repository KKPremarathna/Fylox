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
    default:
      return null;
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
            <p style={{ marginTop: item.event_type.startsWith("REFUND_REVIEW") ? "0.35rem" : "0" }}>
              {item.message}
            </p>
            <time dateTime={item.created_at}>
              {formatDate(item.created_at)}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}