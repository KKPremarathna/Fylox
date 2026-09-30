import { useState, type FormEvent } from "react";

type CreateTicketFormProps = {
  onSubmit: (subject: string, description: string) => Promise<void>;
};

export function CreateTicketForm({
  onSubmit,
}: CreateTicketFormProps) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError(null);

    if (subject.trim().length < 5) {
      setError("Subject must contain at least 5 characters.");
      return;
    }

    if (description.trim().length < 10) {
      setError("Description must contain at least 10 characters.");
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit(subject.trim(), description.trim());

      setSubject("");
      setDescription("");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to create the ticket.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">NEW REQUEST</p>
          <h2>Create a support ticket</h2>
        </div>
      </div>

      <form className="ticket-form" onSubmit={handleSubmit}>
        <label htmlFor="ticket-subject">Subject</label>
        <input
          id="ticket-subject"
          type="text"
          minLength={5}
          maxLength={150}
          placeholder="For example: I was charged twice"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          required
        />

        <label htmlFor="ticket-description">Describe the issue</label>
        <textarea
          id="ticket-description"
          minLength={10}
          maxLength={2000}
          rows={5}
          placeholder="Give us the details that will help support investigate."
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          required
        />

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="form-actions">
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating ticket..." : "Create ticket"}
          </button>
        </div>
      </form>
    </section>
  );
}