import type { TicketStatus } from "../types/api";

type TicketFilter = "ALL" | TicketStatus;

type TicketFiltersProps = {
  value: TicketFilter;
  onChange: (value: TicketFilter) => void;
};

const filters: Array<{
  label: string;
  value: TicketFilter;
}> = [
  { label: "All", value: "ALL" },
  { label: "Open", value: "OPEN" },
  { label: "In progress", value: "IN_PROGRESS" },
  { label: "Resolved", value: "RESOLVED" },
  { label: "Closed", value: "CLOSED" },
];

export function TicketFilters({
  value,
  onChange,
}: TicketFiltersProps) {
  return (
    <div className="ticket-filters" aria-label="Filter tickets by status">
      {filters.map((filter) => (
        <button
          className={
            value === filter.value
              ? "filter-button filter-button-active"
              : "filter-button"
          }
          key={filter.value}
          type="button"
          onClick={() => onChange(filter.value)}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}