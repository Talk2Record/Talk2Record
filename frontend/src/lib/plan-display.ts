import type { PlanCatalogItem, SupportedCurrency } from "@/types/platform";
import { formatCurrency } from "@/lib/format";

export type PlanChangeKind = "current" | "upgrade" | "downgrade" | "new";

const FEATURE_LABELS: Record<string, string> = {
  "basic-capture": "WhatsApp voice capture",
  "billing-portal": "Billing portal",
  "email-support": "Email support",
  "team-workflows": "Team workflows",
  analytics: "Analytics suite",
  "priority-email-support": "Priority email support",
  "advanced-integrations": "Advanced integrations",
  "webhook-workflows": "Webhook workflows",
  "billing-controls": "Billing controls",
};

function humanizeSlug(value: string): string {
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatPlanFeatureLines(plan: PlanCatalogItem): string[] {
  const lines: string[] = [];

  const usage = plan.entitlements.find((row) => row.feature_key === "ai.usage" && row.enabled);
  if (usage && usage.limit > 0) {
    lines.push(`${usage.limit.toLocaleString()} voice notes / month`);
  }

  const seats = plan.entitlements.find((row) => row.feature_key === "team.seats" && row.enabled);
  if (seats && seats.limit > 0) {
    lines.push(`${seats.limit} team seat${seats.limit === 1 ? "" : "s"}`);
  }

  for (const feature of plan.features) {
    const label = FEATURE_LABELS[feature] ?? humanizeSlug(feature);
    if (!lines.includes(label)) {
      lines.push(label);
    }
  }

  return lines.slice(0, 5);
}

export function formatPlanMonthlyPrice(
  plan: PlanCatalogItem,
  displayCurrency?: SupportedCurrency
): string {
  const currency = displayCurrency ?? plan.currency;
  return `${formatCurrency(plan.monthlyPrice, currency)} /mo`;
}

export function comparePlanChange(
  currentPlanCode: string | null | undefined,
  target: PlanCatalogItem,
  plans: PlanCatalogItem[]
): PlanChangeKind {
  if (!currentPlanCode) return "new";
  if (currentPlanCode === target.code) return "current";

  const ordered = [...plans].sort((a, b) => a.monthlyPrice - b.monthlyPrice);
  const current = ordered.find((plan) => plan.code === currentPlanCode);
  if (!current) return "new";

  if (target.monthlyPrice > current.monthlyPrice) return "upgrade";
  if (target.monthlyPrice < current.monthlyPrice) return "downgrade";
  return "new";
}

export function findHighlightedPlan(plans: PlanCatalogItem[]): PlanCatalogItem | undefined {
  return plans.find((plan) => plan.isHighlighted) ?? plans[Math.floor(plans.length / 2)];
}

export function formatPlanTrialLabel(plan: PlanCatalogItem): string | null {
  const monthly = plan.prices.find((price) => price.interval === "month" && price.active);
  const trial = monthly?.trialPeriod;
  if (!trial || trial.frequency <= 0) {
    return null;
  }

  const unit = trial.interval === "day" ? "day" : trial.interval;
  const plural = trial.frequency === 1 ? unit : `${unit}s`;
  return `${trial.frequency}-${plural} free trial`;
}
