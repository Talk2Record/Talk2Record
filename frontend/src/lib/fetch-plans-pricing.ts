import { normalizeApiBaseUrl } from "@/lib/api";
import { siteConfig } from "@/shared/lib/config/site";

interface BackendPlanCatalogRow {
  monthly_amount?: number | string;
  base_price?: number | string;
  currency?: string;
}

export interface PlansPricingRange {
  minPrice: string;
  maxPrice: string;
  currency: string;
}

function toNumber(value: number | string | undefined): number | null {
  if (value === undefined || value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export async function fetchPlansPricingRange(): Promise<PlansPricingRange | null> {
  const baseUrl = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

  try {
    const response = await fetch(`${baseUrl}/billing/plans/`, {
      next: { revalidate: 3600 },
    });
    if (!response.ok) return null;

    const plans = (await response.json()) as BackendPlanCatalogRow[];
    const monthlyAmounts = plans
      .map((plan) => toNumber(plan.monthly_amount) ?? toNumber(plan.base_price))
      .filter((amount): amount is number => amount !== null && amount > 0);

    if (!monthlyAmounts.length) return null;

    return {
      minPrice: String(Math.min(...monthlyAmounts)),
      maxPrice: String(Math.max(...monthlyAmounts)),
      currency: plans[0]?.currency ?? siteConfig.pricing.currency,
    };
  } catch {
    return null;
  }
}
