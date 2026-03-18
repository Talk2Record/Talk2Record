"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { billingService } from "@/services/platform-service";
import { formatCurrency, formatDate } from "@/lib/format";
import { trackEvent } from "@/lib/analytics";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export default function BillingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["billing"],
    queryFn: billingService.getSnapshot,
  });
  const [status, setStatus] = useState("");
  const [acceptedBillingTerms, setAcceptedBillingTerms] = useState(false);

  async function checkout(plan: string) {
    trackEvent("billing_upgrade_started", { plan });
    try {
      const response = await billingService.checkout({ plan, acceptedBillingTerms });
      setStatus(response.status);
      if (response.checkoutUrl && !response.checkoutUrl.includes("billing.example.com")) {
        window.location.assign(response.checkoutUrl);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to start checkout.");
    }
  }

  if (isLoading || !data) {
    return <div className="text-muted-foreground">Loading billing...</div>;
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
