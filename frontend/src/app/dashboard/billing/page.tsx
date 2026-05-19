"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { billingService } from "@/services/platform-service";
import { formatCurrency, formatDate } from "@/lib/format";
import { trackEvent } from "@/lib/analytics";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import BillingLoading from "@/app/dashboard/billing/loading";

type BillingProvider = "stripe" | "paddle";

export default function BillingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["billing"],
    queryFn: billingService.getSnapshot,
  });
  const entitlementsQuery = useQuery({
    queryKey: ["billing", "entitlements"],
    queryFn: () => billingService.listEntitlements(),
  });
  const [status, setStatus] = useState("");
  const [acceptedBillingTerms, setAcceptedBillingTerms] = useState(false);
  const [provider, setProvider] = useState<BillingProvider>("stripe");

  async function checkout(plan: string) {
    trackEvent("billing_upgrade_started", { plan, provider });
    try {
      const response = await billingService.checkout({
        plan,
        acceptedBillingTerms,
        provider,
      });
      setStatus(response.status);
      if (response.checkoutUrl && !response.checkoutUrl.includes("billing.example.com")) {
        window.location.assign(response.checkoutUrl);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to start checkout.");
    }
  }

  if (isLoading || !data) {
    return <BillingLoading />;
  }

  const usage =
    data.subscription.includedVoiceNotes > 0
      ? Math.round(
          (data.subscription.voiceNotesProcessed / data.subscription.includedVoiceNotes) * 100
        )
      : 0;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Revenue and billing
        </div>
        <h1>Billing</h1>
        <p className="text-muted-foreground">
          Subscription, invoices, usage, and upgrade flows are scaffolded against the future billing
          endpoints.
        </p>
      </div>

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
          <CardTitle>Upgrade or downgrade</CardTitle>
          <CardDescription>
            Start a provider checkout session from the backend billing API.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <label className="border-primary/10 bg-background/80 text-muted-foreground w-full rounded-xl border p-3 text-sm">
            <span className="flex items-start gap-3">
              <input
                checked={acceptedBillingTerms}
                className="border-primary/20 mt-1 h-4 w-4 rounded"
                onChange={(event) => setAcceptedBillingTerms(event.target.checked)}
                type="checkbox"
              />
              <span>
                You agree to the{" "}
                <Link
                  className="text-primary underline-offset-4 hover:underline"
                  href="/legal/billing-policy"
                >
                  Billing Policy
                </Link>{" "}
                and understand paid plans renew automatically unless canceled before renewal.
              </span>
            </span>
          </label>
          <div className="flex w-full items-center gap-3 text-sm">
            <span className="text-muted-foreground">Provider</span>
            <div className="flex gap-2">
              {(["stripe", "paddle"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setProvider(value)}
                  className={
                    value === provider
                      ? "bg-primary text-primary-foreground rounded-full px-3 py-1"
                      : "border-primary/20 text-muted-foreground hover:bg-muted rounded-full border px-3 py-1"
                  }
                >
                  {value === "stripe" ? "Stripe" : "Paddle"}
                </button>
              ))}
            </div>
          </div>
          <Button className="rounded-xl" onClick={() => checkout("Starter")} variant="outline">
            Move to Starter
          </Button>
          <Button className="rounded-xl" onClick={() => checkout("Growth")}>
            Move to Growth
          </Button>
          <Button className="rounded-xl" onClick={() => checkout("Scale")} variant="outline">
            Move to Scale
          </Button>
          {status ? <p className="text-muted-foreground w-full text-sm">{status}</p> : null}
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
    </div>
  );
}
