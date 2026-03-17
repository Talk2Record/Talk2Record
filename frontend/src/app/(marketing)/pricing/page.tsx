"use client";

import { formatCurrency } from "@/lib/format";
import { usePreferencesStore } from "@/store/preferences-store";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

const plans = [
  {
    name: "Starter",
    price: 19,
    features: ["500 notes / month", "Basic dashboard", "WhatsApp capture", "Email support"],
  },
  {
    name: "Growth",
    price: 49,
    features: ["1,500 notes / month", "Analytics suite", "Stripe + Sheets", "Priority review queue"],
  },
  {
    name: "Scale",
    price: 99,
    features: ["5,000 notes / month", "Advanced integrations", "Webhook workflows", "Billing controls"],
  },
];

export default function PricingPage() {
  const currency = usePreferencesStore((state) => state.currency);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="max-w-3xl space-y-3">
        <h1>Pricing built for international SaaS teams</h1>
        <p className="text-muted-foreground">
          Localized pricing, usage-aware billing, and upgrade paths that can map directly to Stripe or Paddle later.
        </p>
      </div>
      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.name}>
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <CardDescription>{formatCurrency(plan.price, currency)} monthly base</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2 text-sm text-muted-foreground">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <Button className="w-full">{plan.name === "Growth" ? "Most popular" : "Choose plan"}</Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
