"use client";

import { cn } from "@/shared/lib/utils";
import type { BillingInterval } from "@/types/platform";

interface BillingIntervalToggleProps {
  value: BillingInterval;
  onChange: (_interval: BillingInterval) => void;
  /**
   * Optional savings percent shown next to the "Yearly" button (e.g.
   * "Save 20%"). The plan-catalog grid passes the largest annual saving
   * across its plans to motivate switching.
   */
  annualSavingsPercent?: number;
  className?: string;
}

/**
 * Two-state segmented control for "Monthly / Yearly" pricing. Sized for
 * inline placement above a plan-catalog grid or pricing modal.
 *
 * Accessibility notes:
 *
 * - ``role="tablist"`` so screen readers announce the segmented nature.
 * - Each option is a ``role="tab"`` button with ``aria-selected`` so the
 *   currently active interval is exposed.
 */
export function BillingIntervalToggle({
  value,
  onChange,
  annualSavingsPercent,
  className,
}: BillingIntervalToggleProps) {
  return (
    <div
      role="tablist"
      aria-label="Billing interval"
      className={cn(
        "border-border bg-muted/30 inline-flex items-center gap-1 rounded-full border p-1 text-sm",
        className
      )}
    >
      <button
        type="button"
        role="tab"
        aria-selected={value === "month"}
        onClick={() => onChange("month")}
        className={cn(
          "focus-visible:ring-primary rounded-full px-3 py-1.5 text-xs font-medium transition focus:outline-none focus-visible:ring-2",
          value === "month"
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        Monthly
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === "year"}
        onClick={() => onChange("year")}
        className={cn(
          "focus-visible:ring-primary rounded-full px-3 py-1.5 text-xs font-medium transition focus:outline-none focus-visible:ring-2",
          value === "year"
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <span>Yearly</span>
        {annualSavingsPercent && annualSavingsPercent > 0 ? (
          <span
            className={cn(
              "ml-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
              value === "year"
                ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300"
                : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
            )}
            aria-label={`Save ${annualSavingsPercent}% with yearly billing`}
          >
            Save {annualSavingsPercent}%
          </span>
        ) : null}
      </button>
    </div>
  );
}
