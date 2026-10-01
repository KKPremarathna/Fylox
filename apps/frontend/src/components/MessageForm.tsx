import { useState, type FormEvent } from "react";

type MessageFormProps = {
  onSubmit: (content: string) => Promise<void>;
  onAiSubmit?: (content: string) => Promise<void>;
};

export function MessageForm({
  onSubmit,
  onAiSubmit,
}: MessageFormProps) {
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAiSubmitting, setIsAiSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const trimmedContent = content.trim();

    if (!trimmedContent) {
      setError("Write a message before sending.");
      return;
    }

    if (trimmedContent.length > 5000) {
      setError("A message cannot exceed 5000 characters.");
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit(trimmedContent);
      setContent("");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to send the message.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="message-form" onSubmit={handleSubmit}>
      <label htmlFor="ticket-message">
        Reply to this ticket
      </label>

      <textarea
        id="ticket-message"
        rows={4}
        maxLength={5000}
        placeholder="Add any detail that will help resolve this issue."
        value={content}
        onChange={(event) => setContent(event.target.value)}
        required
      />

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="form-actions" style={{ display: 'flex', gap: '8px' }}>
        <button type="submit" disabled={isSubmitting || isAiSubmitting}>
          {isSubmitting ? "Sending..." : "Send message"}
        </button>
        {onAiSubmit && (
          <button 
            type="button" 
            className="secondary-button"
            disabled={isSubmitting || isAiSubmitting}
            onClick={async () => {
              setError(null);
              const trimmedContent = content.trim();
              if (!trimmedContent) {
                setError("Write a message before asking AI.");
                return;
              }
              if (trimmedContent.length > 5000) {
                setError("A message cannot exceed 5000 characters.");
                return;
              }
              setIsAiSubmitting(true);
              try {
                await onAiSubmit(trimmedContent);
                setContent("");
              } catch (caughtError) {
                setError(
                  caughtError instanceof Error
                    ? caughtError.message
                    : "AI is unavailable right now. Please continue with a human agent."
                );
              } finally {
                setIsAiSubmitting(false);
              }
            }}
          >
            {isAiSubmitting ? "Generating..." : "Ask AI about this ticket"}
          </button>
        )}
      </div>
    </form>
  );
}