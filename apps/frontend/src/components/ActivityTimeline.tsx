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

export function ActivityTimeline({
  activity,
}: ActivityTimelineProps) {
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
            <p>{item.message}</p>
            <time dateTime={item.created_at}>
              {formatDate(item.created_at)}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}