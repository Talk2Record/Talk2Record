"use client";

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

  async function checkout(plan: string) {
    trackEvent("billing_upgrade_started", { plan });
    const response = await billingService.checkout({ plan });
    setStatus(response.status);
  }

  if (isLoading || !data) {
    return <div>Loading billing...</div>;
  }

  const usage = Math.round(
    (data.subscription.voiceNotesProcessed / data.subscription.includedVoiceNotes) * 100
  );

  return (
    <div className="space-y-6">
      <div>
        <h1>Billing</h1>
        <p className="text-muted-foreground">
          Subscription, invoices, usage, and upgrade flows are scaffolded against the future billing endpoints.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{data.subscription.plan}</CardTitle>
            <CardDescription>Current subscription plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-3xl font-semibold">{formatCurrency(data.subscription.amount, currency)}</p>
            <p className="text-sm text-muted-foreground">Renews on {formatDate(data.subscription.renewalDate)}</p>
          </CardContent>
        </Card>
        <Card>
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
        <Card>
          <CardHeader>
            <CardTitle>Seats</CardTitle>
            <CardDescription>Active team members</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{data.subscription.seats}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upgrade or downgrade</CardTitle>
          <CardDescription>Mock checkout flow for Stripe/Paddle handoff.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button onClick={() => checkout("Starter")} variant="outline">
            Move to Starter
          </Button>
          <Button onClick={() => checkout("Growth")}>Move to Growth</Button>
          <Button onClick={() => checkout("Scale")} variant="outline">
            Move to Scale
          </Button>
          {status ? <p className="w-full text-sm text-muted-foreground">{status}</p> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Invoices</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.invoices.map((invoice) => (
            <div key={invoice.id} className="flex items-center justify-between rounded-xl border p-4">
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
