import { useState, type FormEvent } from "react";

type MessageFormProps = {
  onSubmit: (content: string) => Promise<void>;
};

export function MessageForm({
  onSubmit,
}: MessageFormProps) {
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

      <div className="form-actions">
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Sending..." : "Send message"}
        </button>
      </div>
    </form>
  );
}