import { cn } from "@/shared/lib/utils";
import type { RecordStatus } from "@/types/platform";

interface StatusMeta {
  label: string;
  className: string;
}

const STATUS_META: Record<RecordStatus, StatusMeta> = {
  received: {
    label: "Received",
    className: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  },
  transcribing: {
    label: "Transcribing",
    className: "bg-blue-500/10 text-blue-700 dark:text-blue-300",
  },
  transcribed: {
    label: "Transcribed",
    className: "bg-blue-500/10 text-blue-700 dark:text-blue-300",
  },
  extracting: {
    label: "Extracting",
    className: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
  },
  extracted: {
    label: "Extracted",
    className: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
  },
  stored: {
    label: "Stored",
    className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  },
  review: {
    label: "Needs review",
    className: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  },
  failed: {
    label: "Failed",
    className: "bg-destructive/10 text-destructive",
  },
  dead_letter: {
    label: "Dead letter",
    className: "bg-destructive/10 text-destructive",
  },
};

interface RecordStatusBadgeProps {
  status: RecordStatus;
  className?: string;
}

/**
 * Color-coded pill for a record's pipeline status. Uses the same palette as
 * the rest of the dashboard (Tailwind tokens) so it works in light + dark.
 */
export function RecordStatusBadge({ status, className }: RecordStatusBadgeProps) {
  const meta = STATUS_META[status] ?? STATUS_META.received;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        meta.className,
        className
      )}
    >
      {!isTerminal(status) ? (
        <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      ) : null}
      {meta.label}
    </span>
  );
}

function isTerminal(status: RecordStatus): boolean {
  return status === "stored" || status === "failed" || status === "dead_letter";
}
