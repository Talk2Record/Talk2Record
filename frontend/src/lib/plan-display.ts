import type { BillingInterval, PlanCatalogItem, SupportedCurrency } from "@/types/platform";
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

/**
 * Look up the active ``PlanPrice`` row for a given ``interval``. Falls back
 * gracefully so callers can render something even when the plan only
 * publishes one cadence today.
 */
function findActivePrice(plan: PlanCatalogItem, interval: BillingInterval) {
  return (
    plan.prices.find((price) => price.interval === interval && price.active) ??
    plan.prices.find((price) => price.interval === interval) ??
    null
  );
}

/**
 * Format a plan's price for the requested ``interval``.
 *
 * - For ``"month"`` we always show ``$X/mo`` so monthly is the easy compare.
 * - For ``"year"`` we show ``$Y/yr ($Y/12 /mo)`` because users care about
 *   the monthly-equivalent saved by paying annually.
 *
 * Falls back to the plan's stored ``monthlyPrice`` (× 12 for annual) when
 * there's no explicit annual ``PlanPrice`` row — that way the UI still
 * renders gracefully during catalog setup.
 */
export function formatPlanPriceForInterval(
  plan: PlanCatalogItem,
  interval: BillingInterval,
  displayCurrency?: SupportedCurrency
): string {
  const currency = displayCurrency ?? plan.currency;
  if (interval === "month") {
    const price = findActivePrice(plan, "month");
    const amount = price ? price.amount : plan.monthlyPrice;
    return `${formatCurrency(amount, currency)} /mo`;
  }

  const annualPrice = findActivePrice(plan, "year");
  const annualAmount = annualPrice ? annualPrice.amount : plan.monthlyPrice * 12;
  const monthlyEquivalent = annualAmount / 12;
  return `${formatCurrency(annualAmount, currency)} /yr (${formatCurrency(
    monthlyEquivalent,
    currency
  )} /mo)`;
}

/**
 * Discount percentage from picking annual over 12× monthly. Returns ``0``
 * when no saving applies (either no annual price published or annual ≥
 * monthly × 12). Rounded to the nearest integer for badge display.
 */
export function annualSavingsPercent(plan: PlanCatalogItem): number {
  const monthly = findActivePrice(plan, "month");
  const annual = findActivePrice(plan, "year");
  if (!monthly || !annual || monthly.amount <= 0) {
    return 0;
  }
  const twelveMonths = monthly.amount * 12;
  if (annual.amount >= twelveMonths) {
    return 0;
  }
  const saved = twelveMonths - annual.amount;
  return Math.round((saved / twelveMonths) * 100);
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

/**
 * Render the "N-day free trial" label for a plan's active price row. The
 * ``interval`` arg is optional for backwards compatibility — callers that
 * don't pass it default to the monthly trial (most plans only configure
 * their trial on the monthly cadence anyway).
 */
export function formatPlanTrialLabel(
  plan: PlanCatalogItem,
  interval: BillingInterval = "month"
): string | null {
  const price = findActivePrice(plan, interval);
  const trial = price?.trialPeriod;
  if (!trial || trial.frequency <= 0) {
    return null;
  }

  const unit = trial.interval === "day" ? "day" : trial.interval;
  const plural = trial.frequency === 1 ? unit : `${unit}s`;
  return `${trial.frequency}-${plural} free trial`;
}
