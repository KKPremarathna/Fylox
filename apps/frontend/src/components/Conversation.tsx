import type { TicketMessage } from "../types/api";

type ConversationProps = {
  messages: TicketMessage[];
  currentUserId: number | undefined;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function Conversation({
  messages,
  currentUserId,
}: ConversationProps) {
  if (messages.length === 0) {
    return (
      <div className="conversation-empty">
        No messages yet. Add details to start the conversation.
      </div>
    );
  }

  return (
    <div className="conversation">
      {messages.map((message) => {
        const isCurrentUser = message.sender_id === currentUserId;
        const senderName =
          message.sender_type === "AI"
            ? "AI Assistant"
            : message.sender_type === "ADMIN"
              ? "Support team"
              : isCurrentUser
                ? "You"
                : "Customer";

        return (
          <article
            className={[
              "message-bubble",
              isCurrentUser || message.sender_type === "AI"
                ? "message-bubble-own"
                : "message-bubble-other",
              message.sender_type === "AI" ? "message-bubble-ai" : "",
            ].join(" ")}
            key={message.id}
          >
            <div className="message-meta">
              <strong>{senderName}</strong>
              <span>{formatDate(message.created_at)}</span>
            </div>

            <p style={{ whiteSpace: "pre-wrap" }}>{message.content}</p>
          </article>
        );
      })}
    </div>
  );
}