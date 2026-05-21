"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import {
  handleChangePlanSuccess,
  invalidateBillingQueries,
  useChangePlan,
} from "@/shared/hooks/use-change-plan";
import { useAuth } from "@/shared/lib/auth/auth-context";
import {
  formatPlanFeatureLines,
  formatPlanPriceForInterval,
  formatPlanTrialLabel,
  type PlanChangeKind,
} from "@/lib/plan-display";
import { usePreferencesStore } from "@/store/preferences-store";
import type { BillingInterval, PlanCatalogItem } from "@/types/platform";

interface PlanChangeModalProps {
  open: boolean;
  plan: PlanCatalogItem | null;
  changeKind: PlanChangeKind;
  successUrl?: string;
  /** Selected billing interval. Defaults to ``"month"`` for callers that
   * haven't migrated yet. */
  interval?: BillingInterval;
  onOpenChange: (_open: boolean) => void;
}

export function PlanChangeModal({
  open,
  plan,
  changeKind,
  successUrl,
  interval = "month",
  onOpenChange,
}: PlanChangeModalProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const currency = usePreferencesStore((state) => state.currency);
  const changePlan = useChangePlan();
  const [acceptedBillingTerms, setAcceptedBillingTerms] = useState(
    user?.legal?.has_required_billing_acceptance ?? false
  );

  const isCheckout = changeKind === "new";
  const intervalLabel = interval === "year" ? "yearly" : "monthly";
  const title =
    changeKind === "upgrade"
      ? `Upgrade to ${plan?.name ?? ""}`
      : changeKind === "downgrade"
        ? `Switch to ${plan?.name ?? ""}`
        : `Subscribe to ${plan?.name ?? ""}`;

  const trialLabel = plan ? formatPlanTrialLabel(plan, interval) : null;
  // Trial CTA copy lives separately because the user is NOT charged today —
  // they only enter billing info that gets charged when the trial ends.
  const description = trialLabel
    ? `Start your ${trialLabel} on ${intervalLabel} billing. You won't be charged today — Paddle securely captures your payment method and your subscription becomes active when the trial ends.`
    : isCheckout
      ? `A secure Paddle checkout will open so you can complete payment for the ${intervalLabel} plan.`
      : `Your ${intervalLabel} plan changes immediately. Paddle may prorate the difference on your next invoice.`;

  function handleSubmit() {
    if (!plan) return;
    changePlan.mutate(
      { plan: plan.code, acceptedBillingTerms, successUrl, interval },
      {
        onSuccess: (response) => {
          invalidateBillingQueries(queryClient);
          handleChangePlanSuccess(response, {
            onClose: () => onOpenChange(false),
            successUrl,
          });
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {plan ? (
          <div className="border-border bg-muted/30 space-y-3 rounded-xl border p-4">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-sm font-medium">
                {interval === "year" ? "Yearly price" : "Monthly price"}
              </p>
              <p className="text-2xl font-semibold">
                {formatPlanPriceForInterval(plan, interval, currency)}
              </p>
            </div>
            {trialLabel ? (
              <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
                Includes {trialLabel} — you can cancel any time before it ends.
              </p>
            ) : null}
            <ul className="text-muted-foreground list-disc space-y-1 pl-5 text-xs">
              {formatPlanFeatureLines(plan).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <label className="border-border flex items-start gap-3 rounded-xl border p-3 text-sm">
          <input
            type="checkbox"
            checked={acceptedBillingTerms}
            onChange={(event) => setAcceptedBillingTerms(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border"
          />
          <span className="text-muted-foreground">
            I agree to the{" "}
            <Link
              className="text-primary hover:underline"
              href="/legal/billing-policy"
              target="_blank"
            >
              Billing Policy
            </Link>{" "}
            and understand paid plans renew automatically unless canceled before renewal.
          </span>
        </label>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={changePlan.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!plan || !acceptedBillingTerms || changePlan.isPending}
          >
            {changePlan.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isCheckout
                  ? trialLabel
                    ? "Starting trial…"
                    : "Opening checkout…"
                  : "Updating plan…"}
              </>
            ) : isCheckout ? (
              trialLabel ? (
                `Start ${trialLabel}`
              ) : (
                "Continue to checkout"
              )
            ) : (
              "Confirm plan change"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
