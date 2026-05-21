import { AlertTriangle, CreditCard, PauseCircle, Sparkles } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";
import { TrialBanner } from "@/components/billing/trial-banner";
import type { BillingInterval, SubscriptionStatus, SupportedCurrency } from "@/types/platform";

interface SubscriptionBannerProps {
  status: SubscriptionStatus | undefined;
  /** ISO-8601 timestamp for the current period end; used by the trial banner. */
  periodEnd?: string | null;
  /** ISO-8601 trial end timestamp. Distinct from ``periodEnd`` because the
   * billing snapshot stamps it separately when ``status="trialing"``. */
  trialEndsAt?: string | null;
  /** Price + interval that will be charged once the trial converts. */
  amount?: number;
  currency?: SupportedCurrency;
  interval?: BillingInterval;
  onCta?: () => void;
}

interface BannerSpec {
  Icon: typeof AlertTriangle;
  tone: "info" | "warning" | "danger" | "muted";
  title: string;
  description: string;
  cta?: string;
}

function specFor(
  status: SubscriptionStatus | undefined,
  periodEnd?: string | null
): BannerSpec | null {
  switch (status) {
    case "trialing":
      return {
        Icon: Sparkles,
        tone: "info",
        title: periodEnd ? `Trial active — ends ${formatTrialEnd(periodEnd)}` : "Trial active",
        description: "Upgrade any time to keep your team on the platform without interruption.",
        cta: "Upgrade",
      };
    case "past_due":
      return {
        Icon: AlertTriangle,
        tone: "danger",
        title: "Payment failed",
        description:
          "We could not charge the card on file. Update your billing method to keep access.",
        cta: "Update payment",
      };
    case "paused":
      return {
        Icon: PauseCircle,
        tone: "warning",
        title: "Subscription paused",
        description: "Your workspace is read-only until you resume the subscription.",
        cta: "Resume",
      };
    case "canceled":
      return {
        Icon: CreditCard,
        tone: "muted",
        title: "Subscription canceled",
        description: "Reactivate to restore full access to records, analytics, and integrations.",
        cta: "Reactivate",
      };
    default:
      return null;
  }
}

const TONE_CLASSES: Record<BannerSpec["tone"], string> = {
  info: "border-sky-500/30 bg-sky-500/10 text-sky-900 dark:text-sky-100",
  warning: "border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-100",
  danger: "border-destructive/40 bg-destructive/10 text-destructive",
  muted: "border-border bg-muted/40 text-muted-foreground",
};

export function SubscriptionBanner({
  status,
  periodEnd,
  trialEndsAt,
  amount,
  currency,
  interval,
  onCta,
}: SubscriptionBannerProps) {
  // Trialing has its own dedicated banner — it needs to communicate the
  // "no charge today" promise and the conversion price, which doesn't fit
  // the generic banner shell.
  if (status === "trialing") {
    const trialIso = trialEndsAt ?? periodEnd ?? null;
    if (!trialIso) return null;
    return (
      <TrialBanner
        trialEndsAt={trialIso}
        amount={amount}
        currency={currency}
        interval={interval}
        onManageBilling={onCta}
      />
    );
  }

  const spec = specFor(status, periodEnd);
  if (!spec) return null;

  const { Icon } = spec;
  return (
    <div
      className={cn("flex items-start gap-3 rounded-2xl border p-4", TONE_CLASSES[spec.tone])}
      role="status"
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="flex-1 text-sm">
        <p className="font-semibold">{spec.title}</p>
        <p className="opacity-90">{spec.description}</p>
      </div>
      {spec.cta && onCta ? (
        <Button size="sm" variant={spec.tone === "danger" ? "default" : "outline"} onClick={onCta}>
          {spec.cta}
        </Button>
      ) : null}
    </div>
  );
}

/**
 * Format the trial end timestamp into a short "Jan 5" style string. Uses
 * `Intl.DateTimeFormat` which is deterministic given a fixed timestamp, so
 * we can call it during render without violating React's purity rule.
 */
function formatTrialEnd(periodEnd: string): string {
  const date = new Date(periodEnd);
  if (Number.isNaN(date.getTime())) return periodEnd;
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}
