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
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="max-w-3xl space-y-4">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
          Simple plans
        </div>
        <h1>Pricing built for calm operations, not pricing confusion</h1>
        <p className="text-muted-foreground text-lg">
          Start with a lightweight team workflow, then scale into analytics, integrations, and higher processing volume as your business grows.
        </p>
      </div>
      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        {plans.map((plan) => (
          <Card
            key={plan.name}
            className={plan.name === "Growth" ? "border-primary/30 shadow-(--shadow-md)" : "border-primary/10"}
          >
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>{plan.name}</CardTitle>
                {plan.name === "Growth" ? (
                  <span className="bg-primary/10 text-primary rounded-full px-2.5 py-1 text-xs font-medium">
                    Best for growing teams
                  </span>
                ) : null}
              </div>
              <CardDescription>{formatCurrency(plan.price, currency)} monthly base</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2 text-sm text-muted-foreground">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <Button className="w-full rounded-xl" variant={plan.name === "Growth" ? "default" : "outline"}>
                {plan.name === "Growth" ? "Start with Growth" : "Choose plan"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
