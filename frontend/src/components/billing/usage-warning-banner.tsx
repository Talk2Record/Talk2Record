"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { AlertOctagon, AlertTriangle } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { toast } from "@/shared/hooks/use-toast";
import { useUsage } from "@/shared/hooks/use-usage";

/**
 * Persistent banner that lives between the topbar and the page content.
 *
 *   - `exceeded` → red destructive banner, always visible until the user
 *     upgrades or the period resets.
 *   - `approaching` → no banner, but we fire a one-time toast per session
 *     so the user notices.
 *   - `ok` → no banner.
 */
export function UsageWarningBanner() {
  const usage = useUsage();
  const warnedRef = useRef(false);

  useEffect(() => {
    if (warnedRef.current) return;
    if (usage.state !== "approaching") return;
    warnedRef.current = true;
    toast({
      title: "Approaching your plan limit",
      description: `You've used ${Math.round(usage.ratio * 100)}% of your monthly voice-note quota.`,
    });
  }, [usage.state, usage.ratio]);

  if (usage.state !== "exceeded") return null;

  return (
    <div className="border-destructive/30 bg-destructive/10 text-destructive border-b px-4 py-2 md:px-8">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <AlertOctagon className="h-4 w-4 shrink-0" />
        <span className="flex-1 font-medium">
          You've hit your plan's voice-note limit ({usage.processed}/{usage.included}). New ingests
          may be queued or rejected.
        </span>
        <Button asChild size="sm" variant="destructive" className="rounded-xl">
          <Link href="/dashboard/billing">Upgrade plan</Link>
        </Button>
      </div>
    </div>
  );
}

/**
 * Inline soft-guard for buttons that trigger AI work. Returns the props the
 * caller should spread onto the trigger element when the user is at quota.
 */
export function useUsageActionGuard() {
  const usage = useUsage();
  const blocked = usage.state === "exceeded";
  return {
    blocked,
    /**
     * Spread onto a button to disable it with a descriptive tooltip / aria-
     * label and show a friendly toast if the user clicks anyway. Suitable
     * for the upcoming "Create record" entry points.
     */
    actionProps: blocked
      ? {
          disabled: true,
          "aria-disabled": true,
          title: "Plan limit reached. Upgrade to keep ingesting voice notes.",
        }
      : {},
  };
}

export function QuotaExceededInline() {
  return (
    <div className="border-destructive/30 bg-destructive/10 text-destructive flex items-center gap-2 rounded-xl border p-3 text-sm">
      <AlertTriangle className="h-4 w-4" />
      <span>Plan limit reached. Upgrade to continue.</span>
    </div>
  );
}
