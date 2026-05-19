"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { billingService } from "@/services/platform-service";
import { formatCurrency, formatDate } from "@/lib/format";
import {
  comparePlanChange,
  findHighlightedPlan,
  type PlanChangeKind,
} from "@/lib/plan-display";
import { trackEvent } from "@/lib/analytics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import BillingLoading from "@/app/dashboard/billing/loading";
import { SubscriptionBanner } from "@/components/billing/subscription-banner";
import { PlanCatalogGrid } from "@/components/billing/plan-catalog-grid";
import { PlanChangeModal } from "@/components/billing/plan-change-modal";
import { usePlans } from "@/shared/hooks/use-plans";
import { toast } from "@/shared/hooks/use-toast";
import type { PlanCatalogItem, SubscriptionStatus } from "@/types/platform";

export default function BillingPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();

  const billingQuery = useQuery({
    queryKey: ["billing"],
    queryFn: billingService.getSnapshot,
  });
  const { plans, isLoading: plansLoading } = usePlans();
  const entitlementsQuery = useQuery({
    queryKey: ["billing", "entitlements"],
    queryFn: () => billingService.listEntitlements(),
  });
  const subscriptionsQuery = useQuery({
    queryKey: ["billing", "subscriptions"],
    queryFn: () => billingService.listSubscriptions(),
  });

  const [selectedPlan, setSelectedPlan] = useState<PlanCatalogItem | null>(null);
  const [changeKind, setChangeKind] = useState<PlanChangeKind>("new");

  // Handle the `?checkout=success|cancelled` return from Paddle.
  useEffect(() => {
    const checkoutResult = searchParams?.get("checkout");
    if (!checkoutResult) return;

    if (checkoutResult === "success") {
      toast({
        title: "Subscription updated",
        description: "Your new plan will appear in a moment.",
      });
      void queryClient.invalidateQueries({ queryKey: ["billing"] });
      void queryClient.invalidateQueries({ queryKey: ["billing", "entitlements"] });
      void queryClient.invalidateQueries({ queryKey: ["billing", "subscriptions"] });
      trackEvent("billing_checkout_returned", { result: "success" });
    } else {
      toast({
        title: "Checkout cancelled",
        description: "No changes were made to your subscription.",
        variant: "destructive",
      });
      trackEvent("billing_checkout_returned", { result: "cancelled" });
    }

    // Strip the param so refreshes don't re-fire the toast.
    router.replace("/dashboard/billing");
  }, [searchParams, queryClient, router]);

  const currentSubscription = subscriptionsQuery.data?.[0];
  const subscriptionStatus: SubscriptionStatus | undefined = currentSubscription?.status;
  const subscriptionPeriodEnd = currentSubscription?.current_period_end ?? null;

  if (billingQuery.isLoading || !billingQuery.data) {
    return <BillingLoading />;
  }
  const data = billingQuery.data;
  const currentPlanCode =
    data.subscription.planCode ?? currentSubscription?.plan_code ?? null;

  const usage =
    data.subscription.includedVoiceNotes > 0
      ? Math.round(
          (data.subscription.voiceNotesProcessed / data.subscription.includedVoiceNotes) * 100
        )
      : 0;

  function openPlanChange(plan: PlanCatalogItem, kind: PlanChangeKind) {
    trackEvent("billing_upgrade_clicked", { plan: plan.code });
    setSelectedPlan(plan);
    setChangeKind(kind);
  }

  function openHighlightedPlan() {
    const highlighted = findHighlightedPlan(plans);
    if (!highlighted) return;
    openPlanChange(highlighted, comparePlanChange(currentPlanCode, highlighted, plans));
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Revenue and billing
        </div>
        <h1>Billing</h1>
        <p className="text-muted-foreground">
          Subscription, invoices, and usage for this workspace.
        </p>
      </div>

      <SubscriptionBanner
        status={subscriptionStatus}
        periodEnd={subscriptionPeriodEnd}
        onCta={openHighlightedPlan}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>{data.subscription.plan}</CardTitle>
            <CardDescription>Current subscription plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-3xl font-semibold">
              {formatCurrency(data.subscription.amount, data.subscription.currency)}
            </p>
            <p className="text-muted-foreground text-sm">
              Renews on {formatDate(data.subscription.renewalDate)}
            </p>
          </CardContent>
        </Card>
        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>Usage</CardTitle>
            <CardDescription>Voice notes processed this cycle</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-3xl font-semibold">{usage}%</p>
            <p className="text-muted-foreground text-sm">
              {data.subscription.voiceNotesProcessed} of {data.subscription.includedVoiceNotes} used
            </p>
          </CardContent>
        </Card>
        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>Seats</CardTitle>
            <CardDescription>Active team members</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{data.subscription.seats}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Change plan</CardTitle>
          <CardDescription>
            Pick a new plan to upgrade, downgrade, or start a secure Paddle checkout.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PlanCatalogGrid
            plans={plans}
            isLoading={plansLoading}
            variant="billing"
            currentPlanCode={currentPlanCode}
            onSelectPlan={openPlanChange}
          />
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Plan features</CardTitle>
          <CardDescription>
            Features and limits granted by your current subscription.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {entitlementsQuery.isLoading ? (
            <p className="text-muted-foreground text-sm">Loading…</p>
          ) : entitlementsQuery.data && entitlementsQuery.data.length > 0 ? (
            <ul className="space-y-1 text-sm">
              {entitlementsQuery.data.map((row) => (
                <li
                  key={row.feature_key}
                  className="border-primary/10 flex items-center justify-between rounded-md border px-3 py-2"
                >
                  <span className="font-medium">{row.feature_key}</span>
                  <span className="text-muted-foreground">
                    {row.enabled
                      ? row.limit > 0
                        ? `${row.limit}${row.period !== "none" ? ` / ${row.period}` : ""}`
                        : "Included"
                      : "Disabled"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground text-sm">No plan features published yet.</p>
          )}
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.invoices.length ? (
            data.invoices.map((invoice) => (
              <div
                key={invoice.id}
                className="border-primary/10 bg-background/80 flex items-center justify-between rounded-2xl border p-4"
              >
                <div>
                  <p className="font-medium">{invoice.id}</p>
                  <p className="text-muted-foreground text-sm">{formatDate(invoice.issuedAt)}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatCurrency(invoice.amount, invoice.currency)}</p>
                  <p className="text-muted-foreground text-sm">{invoice.status}</p>
                </div>
              </div>
            ))
          ) : (
            <p className="text-muted-foreground text-sm">
              No invoices are available for this workspace yet.
            </p>
          )}
        </CardContent>
      </Card>

      <PlanChangeModal
        open={selectedPlan !== null}
        plan={selectedPlan}
        changeKind={changeKind}
        successUrl={
          typeof window !== "undefined"
            ? `${window.location.origin}/dashboard/billing?checkout=success`
            : undefined
        }
        onOpenChange={(open) => {
          if (!open) setSelectedPlan(null);
        }}
      />
    </div>
  );
}
