"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";
import { useAuth } from "@/shared/lib/auth/auth-context";
import {
  comparePlanChange,
  formatPlanFeatureLines,
  formatPlanMonthlyPrice,
  formatPlanTrialLabel,
  type PlanChangeKind,
} from "@/lib/plan-display";
import { cn } from "@/shared/lib/utils";
import type { PlanCatalogItem } from "@/types/platform";
import { usePreferencesStore } from "@/store/preferences-store";

interface PlanCatalogGridProps {
  plans: PlanCatalogItem[];
  isLoading?: boolean;
  variant: "marketing" | "billing";
  currentPlanCode?: string | null;
  onSelectPlan?: (plan: PlanCatalogItem, changeKind: PlanChangeKind) => void;
}

export function PlanCatalogGrid({
  plans,
  isLoading,
  variant,
  currentPlanCode,
  onSelectPlan,
}: PlanCatalogGridProps) {
  const { isAuthenticated } = useAuth();
  const currency = usePreferencesStore((state) => state.currency);

  if (isLoading) {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        {[0, 1, 2].map((index) => (
          <Card key={index} className="border-primary/10">
            <CardHeader>
              <Skeleton className="h-6 w-24" />
              <Skeleton className="mt-2 h-4 w-32" />
            </CardHeader>
            <CardContent className="space-y-2">
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!plans.length) {
    return (
      <p className="text-muted-foreground text-sm">
        Plans are not available right now. Please try again in a moment.
      </p>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {plans.map((plan) => {
        const changeKind = comparePlanChange(currentPlanCode, plan, plans);
        const isCurrent = changeKind === "current";
        const highlighted = plan.isHighlighted;
        const trialLabel = formatPlanTrialLabel(plan);

        return (
          <Card
            key={plan.code}
            className={cn(
              "border-primary/10 flex flex-col",
              highlighted && "border-primary/30 shadow-(--shadow-md)"
            )}
          >
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>{plan.name}</CardTitle>
                {isCurrent ? (
                  <span className="bg-muted text-muted-foreground rounded-full px-2.5 py-1 text-xs font-medium">
                    Current plan
                  </span>
                ) : highlighted ? (
                  <span className="bg-primary/10 text-primary rounded-full px-2.5 py-1 text-xs font-medium">
                    Popular
                  </span>
                ) : changeKind === "upgrade" ? (
                  <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                    Upgrade
                  </span>
                ) : changeKind === "downgrade" ? (
                  <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-800 dark:text-amber-200">
                    Downgrade
                  </span>
                ) : null}
              </div>
              <CardDescription>
                {formatPlanMonthlyPrice(plan, currency)}
                {trialLabel ? (
                  <span className="mt-1 block text-xs font-medium text-emerald-700 dark:text-emerald-300">
                    {trialLabel}
                  </span>
                ) : null}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col gap-4">
              <ul className="text-muted-foreground space-y-2 text-sm">
                {formatPlanFeatureLines(plan).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              {variant === "marketing" ? (
                <Button
                  asChild
                  className="mt-auto w-full rounded-xl"
                  variant={highlighted ? "default" : "outline"}
                >
                  <Link href={isAuthenticated ? "/dashboard/billing" : "/register"}>
                    {isAuthenticated ? "Manage plan" : "Get started"}
                    <ExternalLink className="ml-1 h-3.5 w-3.5" />
                  </Link>
                </Button>
              ) : (
                <Button
                  type="button"
                  className="mt-auto w-full rounded-xl"
                  variant={highlighted && !isCurrent ? "default" : "outline"}
                  disabled={isCurrent}
                  onClick={() => onSelectPlan?.(plan, changeKind)}
                >
                  {isCurrent ? "Current plan" : changeKind === "upgrade" ? "Upgrade" : "Switch plan"}
                </Button>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
