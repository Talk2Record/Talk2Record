"use client";

import Link from "next/link";
import { Activity, ArrowUpRight, CreditCard } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";
import { formatDate } from "@/lib/format";
import { useUsage } from "@/shared/hooks/use-usage";
import { useEntitlement } from "@/shared/hooks/use-entitlement";
import { billingService } from "@/services/platform-service";
import { useQuery } from "@tanstack/react-query";

export default function UsagePage() {
  const usage = useUsage();
  const aiUsageEntitlement = useEntitlement("ai.usage");
  const analyticsEntitlement = useEntitlement("analytics.advanced");

  const entitlementsQuery = useQuery({
    queryKey: ["billing", "entitlements"],
    queryFn: () => billingService.listEntitlements(),
  });

  const percent = Math.min(100, Math.round(usage.ratio * 100));
  const ratioBg =
    usage.state === "exceeded"
      ? "bg-destructive"
      : usage.state === "approaching"
        ? "bg-amber-500"
        : "bg-emerald-500";

  if (usage.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-7 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
          <Activity className="h-3.5 w-3.5" />
          Plan usage
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Usage</h1>
        <p className="text-muted-foreground max-w-2xl text-sm">
          Track how much of your plan you've used this billing cycle. Voice-note ingestion is the
          primary metered resource; other features either have hard or soft limits as listed below.
        </p>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Voice notes this period</CardTitle>
          <CardDescription>
            {usage.renewalDate
              ? `Resets on ${formatDate(usage.renewalDate)}`
              : "Current billing period"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-4xl font-semibold tracking-tight">
              {usage.processed.toLocaleString()}
              <span className="text-muted-foreground ml-2 text-base font-normal">
                / {usage.included.toLocaleString()}
              </span>
            </p>
            <p
              className={
                usage.state === "exceeded"
                  ? "text-destructive text-sm font-semibold"
                  : usage.state === "approaching"
                    ? "text-sm font-semibold text-amber-600 dark:text-amber-400"
                    : "text-sm font-semibold text-emerald-600 dark:text-emerald-400"
              }
            >
              {percent}% used
            </p>
          </div>
          <div className="bg-muted h-3 w-full overflow-hidden rounded-full">
            <div
              className={`h-full ${ratioBg} transition-all`}
              style={{ width: `${percent}%` }}
              role="progressbar"
              aria-label="Voice-note quota usage"
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuetext={`${percent}% used`}
            />
          </div>
          {usage.state === "exceeded" ? (
            <div className="border-destructive/30 bg-destructive/10 text-destructive rounded-xl border p-3 text-sm">
              You've used your full allowance. Until you upgrade, new ingests may be queued or
              rejected by the API.
            </div>
          ) : usage.state === "approaching" ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">
              You're past 70% of your plan. Upgrade before your next surge to avoid service blips.
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button asChild className="rounded-xl">
              <Link href="/dashboard/billing">
                <CreditCard className="mr-1 h-4 w-4" />
                Manage subscription
              </Link>
            </Button>
            <Button asChild variant="outline" className="rounded-xl">
              <Link href="/dashboard/billing">
                View invoices
                <ArrowUpRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Plan features and limits</CardTitle>
          <CardDescription>
            Per-feature entitlements granted by your active subscription.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {entitlementsQuery.isLoading ? (
            <p className="text-muted-foreground text-sm">Loading entitlements…</p>
          ) : entitlementsQuery.data && entitlementsQuery.data.length > 0 ? (
            <ul className="space-y-2 text-sm">
              {entitlementsQuery.data.map((row) => (
                <li
                  key={row.feature_key}
                  className="border-primary/10 flex items-center justify-between rounded-xl border p-3"
                >
                  <div>
                    <p className="font-medium">{row.feature_key}</p>
                    <p className="text-muted-foreground text-xs">
                      {row.enabled ? "Enabled" : "Disabled"}
                      {row.period !== "none" ? ` · resets ${row.period}` : ""}
                    </p>
                  </div>
                  <span className="text-muted-foreground text-sm">
                    {row.enabled ? (row.limit > 0 ? row.limit.toLocaleString() : "Unlimited") : "—"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground text-sm">
              No entitlements published yet. Contact support if you expect features here.
            </p>
          )}
        </CardContent>
      </Card>

      {!analyticsEntitlement.enabled || !aiUsageEntitlement.enabled ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle>Unlock more on a higher plan</CardTitle>
            <CardDescription>
              Upgrade for higher quotas, advanced analytics, and additional AI features.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="rounded-xl">
              <Link href="/dashboard/billing">See plan options</Link>
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
