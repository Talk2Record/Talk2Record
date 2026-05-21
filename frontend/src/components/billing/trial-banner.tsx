"use client";

import { Sparkles } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";
import { formatCurrency } from "@/lib/format";
import type { SupportedCurrency } from "@/types/platform";

interface TrialBannerProps {
  /** ISO-8601 trial end timestamp. */
  trialEndsAt: string;
  /** Amount that will be charged once the trial ends. */
  amount?: number;
  currency?: SupportedCurrency;
  /** Interval label ("month" / "year") — drives the "/mo" or "/yr" copy. */
  interval?: "month" | "year";
  onManageBilling?: () => void;
  className?: string;
}

/**
 * Dedicated trial-period banner. Communicates:
 *
 *   1. how many days are left in the trial,
 *   2. that the user is NOT charged today (Paddle has the card on file),
 *   3. exactly when and how much they'll be billed.
 *
 * Lives alongside (not inside) :file:`subscription-banner.tsx` so the
 * caller can decide where to render it. The billing page renders it
 * prominently above the plan cards; the dashboard sidebar can render a
 * condensed version later.
 */
export function TrialBanner({
  trialEndsAt,
  amount,
  currency,
  interval = "month",
  onManageBilling,
  className,
}: TrialBannerProps) {
  const days = daysUntil(trialEndsAt);
  const endLabel = formatTrialEnd(trialEndsAt);
  const intervalLabel = interval === "year" ? "/yr" : "/mo";
  const priceLabel =
    amount && amount > 0 && currency ? `${formatCurrency(amount, currency)}${intervalLabel}` : null;

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-2xl border border-sky-500/30 bg-sky-500/10 p-4 text-sky-900 dark:text-sky-100",
        className
      )}
      role="status"
      aria-label={`Trial ends ${endLabel}`}
    >
      <Sparkles className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="flex-1 text-sm">
        <p className="font-semibold">
          {days > 0
            ? `Trial ends in ${days} day${days === 1 ? "" : "s"} — ${endLabel}`
            : `Trial ends ${endLabel}`}
        </p>
        <p className="opacity-90">
          You haven&apos;t been charged yet.{" "}
          {priceLabel
            ? `On ${endLabel}, Paddle will charge ${priceLabel} unless you cancel.`
            : `Your card on file will be charged when the trial ends.`}{" "}
          You can cancel at any time before then.
        </p>
      </div>
      {onManageBilling ? (
        <Button size="sm" variant="outline" onClick={onManageBilling}>
          Manage billing
        </Button>
      ) : null}
    </div>
  );
}

function daysUntil(iso: string): number {
  const target = new Date(iso).getTime();
  if (Number.isNaN(target)) return 0;
  const diffMs = target - Date.now();
  return Math.max(0, Math.ceil(diffMs / (24 * 60 * 60 * 1000)));
}

function formatTrialEnd(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
