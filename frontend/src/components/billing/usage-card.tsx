"use client";

import Link from "next/link";
import { ArrowUpRight, Sparkles } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";
import { formatDate } from "@/lib/format";
import { useUsage } from "@/shared/hooks/use-usage";

/**
 * Dashboard widget showing voice-note quota for the current billing cycle.
 * Threshold colors:
 *   - <70%   → green
 *   - 70–95% → amber, with a contextual upsell hint
 *   - ≥95%   → red, with the upgrade CTA pinned
 */
export function UsageCard() {
  const usage = useUsage();
  const percent = Math.min(100, Math.round(usage.ratio * 100));
  const ratioBg =
    usage.state === "exceeded"
      ? "bg-destructive"
      : usage.state === "approaching"
        ? "bg-amber-500"
        : "bg-emerald-500";

  if (usage.isLoading) {
    return (
      <Card className="border-primary/10">
        <CardHeader>
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-3 w-full rounded-full" />
        </CardContent>
      </Card>
    );
  }

  if (usage.included === 0) {
    return null;
  }

  return (
    <Card className="border-primary/10">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div>
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <Sparkles className="h-3.5 w-3.5" />
            Voice-note quota
          </div>
          <CardTitle className="mt-2 text-lg">
            {usage.processed.toLocaleString()} / {usage.included.toLocaleString()}
          </CardTitle>
          <CardDescription>
            {usage.renewalDate
              ? `Resets on ${formatDate(usage.renewalDate)}`
              : "This billing period"}
          </CardDescription>
        </div>
        <Button asChild variant="outline" className="rounded-xl">
          <Link href="/dashboard/usage">
            Details
            <ArrowUpRight className="ml-1 h-3 w-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
          <div
            className={`h-full ${ratioBg} transition-all`}
            style={{ width: `${percent}%` }}
            aria-label={`${percent}% of quota used`}
            role="progressbar"
            aria-valuenow={percent}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        {usage.state !== "ok" ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-muted-foreground text-sm">
              {usage.state === "exceeded"
                ? "You've hit your plan limit. New voice notes may be queued or rejected until you upgrade."
                : "You're approaching your plan limit. Consider upgrading before customers start to feel it."}
            </p>
            <Button asChild size="sm" className="shrink-0 rounded-xl">
              <Link href="/dashboard/billing">Upgrade</Link>
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
