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
import { formatPlanFeatureLines, formatPlanMonthlyPrice, type PlanChangeKind } from "@/lib/plan-display";
import { usePreferencesStore } from "@/store/preferences-store";
import type { PlanCatalogItem } from "@/types/platform";

interface PlanChangeModalProps {
  open: boolean;
  plan: PlanCatalogItem | null;
  changeKind: PlanChangeKind;
  successUrl?: string;
  onOpenChange: (open: boolean) => void;
}

export function PlanChangeModal({
  open,
  plan,
  changeKind,
  successUrl,
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
  const title =
    changeKind === "upgrade"
      ? `Upgrade to ${plan?.name ?? ""}`
      : changeKind === "downgrade"
        ? `Switch to ${plan?.name ?? ""}`
        : `Subscribe to ${plan?.name ?? ""}`;

  const description = isCheckout
    ? "A secure Paddle checkout will open so you can complete payment."
    : "Your plan changes immediately. Paddle may prorate the difference on your next invoice.";

  function handleSubmit() {
    if (!plan) return;
    changePlan.mutate(
      { plan: plan.code, acceptedBillingTerms, successUrl },
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
              <p className="text-sm font-medium">Monthly price</p>
              <p className="text-2xl font-semibold">{formatPlanMonthlyPrice(plan, currency)}</p>
            </div>
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
            <Link className="text-primary hover:underline" href="/legal/billing-policy" target="_blank">
              Billing Policy
            </Link>{" "}
            and understand paid plans renew automatically unless canceled before renewal.
          </span>
        </label>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={changePlan.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!plan || !acceptedBillingTerms || changePlan.isPending}>
            {changePlan.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isCheckout ? "Opening checkout…" : "Updating plan…"}
              </>
            ) : isCheckout ? (
              "Continue to checkout"
            ) : (
              "Confirm plan change"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
