"use client";

import { PlanCatalogGrid } from "@/components/billing/plan-catalog-grid";
import { usePlans } from "@/shared/hooks/use-plans";

export default function PricingPage() {
  const { plans, isLoading } = usePlans();

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="max-w-3xl space-y-4">
        <div className="bg-primary/10 text-primary inline-flex rounded-full px-3 py-1 text-sm font-medium">
          Simple plans
        </div>
        <h1>Pricing built for calm operations, not pricing confusion</h1>
        <p className="text-muted-foreground text-lg">
          Start with a lightweight team workflow, then scale into analytics, integrations, and
          higher processing volume as your business grows.
        </p>
      </div>
      <div className="mt-8">
        <PlanCatalogGrid plans={plans} isLoading={isLoading} variant="marketing" />
      </div>
    </div>
  );
}
