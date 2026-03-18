"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { billingService } from "@/services/platform-service";
import { formatCurrency, formatDate } from "@/lib/format";
import { usePreferencesStore } from "@/store/preferences-store";
import { trackEvent } from "@/lib/analytics";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export default function BillingPage() {
  const currency = usePreferencesStore((state) => state.currency);
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
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to start checkout.");
    }
  }

  if (isLoading || !data) {
    return <div className="text-muted-foreground">Loading billing...</div>;
  }

  const usage = Math.round(
    (data.subscription.voiceNotesProcessed / data.subscription.includedVoiceNotes) * 100
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-xs font-medium">
          Revenue and billing
        </div>
        <h1>Billing</h1>
        <p className="text-muted-foreground">
          Subscription, invoices, usage, and upgrade flows are scaffolded against the future billing endpoints.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>{data.subscription.plan}</CardTitle>
            <CardDescription>Current subscription plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-3xl font-semibold">{formatCurrency(data.subscription.amount, currency)}</p>
            <p className="text-sm text-muted-foreground">Renews on {formatDate(data.subscription.renewalDate)}</p>
          </CardContent>
        </Card>
        <Card className="border-primary/10">
          <CardHeader>
            <CardTitle>Usage</CardTitle>
            <CardDescription>Voice notes processed this cycle</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-3xl font-semibold">{usage}%</p>
            <p className="text-sm text-muted-foreground">
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
          <CardDescription>Mock checkout flow for Stripe/Paddle handoff.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <label className="w-full rounded-xl border border-primary/10 bg-background/80 p-3 text-sm text-muted-foreground">
            <span className="flex items-start gap-3">
              <input
                checked={acceptedBillingTerms}
                className="mt-1 h-4 w-4 rounded border-primary/20"
                onChange={(event) => setAcceptedBillingTerms(event.target.checked)}
                type="checkbox"
              />
              <span>
                You agree to the{" "}
                <Link className="text-primary underline-offset-4 hover:underline" href="/legal/billing-policy">
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
          {status ? <p className="w-full text-sm text-muted-foreground">{status}</p> : null}
        </CardContent>
      </Card>

      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.invoices.map((invoice) => (
            <div key={invoice.id} className="flex items-center justify-between rounded-2xl border border-primary/10 bg-background/80 p-4">
              <div>
                <p className="font-medium">{invoice.id}</p>
                <p className="text-sm text-muted-foreground">{formatDate(invoice.issuedAt)}</p>
              </div>
              <div className="text-right">
                <p className="font-medium">{formatCurrency(invoice.amount, invoice.currency)}</p>
                <p className="text-sm text-muted-foreground">{invoice.status}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
