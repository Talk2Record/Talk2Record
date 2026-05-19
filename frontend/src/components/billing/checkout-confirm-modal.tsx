"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { billingService } from "@/services/platform-service";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { handleChangePlanSuccess } from "@/shared/hooks/use-change-plan";
import { notifyApiError } from "@/shared/lib/notify-api-error";
import { formatPlanFeatureLines, formatPlanMonthlyPrice } from "@/lib/plan-display";
import { trackEvent } from "@/lib/analytics";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { usePreferencesStore } from "@/store/preferences-store";
import type { PlanCatalogItem } from "@/types/platform";

interface CheckoutConfirmModalProps {
  open: boolean;
  plan: PlanCatalogItem | null;
  onOpenChange: (_open: boolean) => void;
}

export function CheckoutConfirmModal({ open, plan, onOpenChange }: CheckoutConfirmModalProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const currency = usePreferencesStore((state) => state.currency);
  const [acceptedBillingTerms, setAcceptedBillingTerms] = useState(
    user?.legal?.has_required_billing_acceptance ?? false
  );

  const checkoutSuccessUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/dashboard/billing?checkout=success`
      : undefined;

  const checkout = useMutation({
    mutationFn: (planCode: string) =>
      billingService.checkout({
        plan: planCode,
        acceptedBillingTerms,
        successUrl: checkoutSuccessUrl,
      }),
    onSuccess: async (response, planCode) => {
      trackEvent("billing_checkout_redirected", { plan: planCode });
      void queryClient.invalidateQueries({ queryKey: ["billing"] });
      await handleChangePlanSuccess(response, {
        onClose: () => onOpenChange(false),
        successUrl: checkoutSuccessUrl,
      });
    },
    onError: (error) => notifyApiError(error, { title: "Checkout failed" }),
  });

  function handleSubmit() {
    if (!plan) return;
    checkout.mutate(plan.code);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upgrade to {plan?.name ?? ""}</DialogTitle>
          <DialogDescription>
            A secure Paddle checkout will open so you can complete payment.
          </DialogDescription>
        </DialogHeader>

        {plan ? (
          <div className="border-border bg-muted/30 mt-4 space-y-3 rounded-xl border p-4">
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

        <label className="border-border mt-4 flex items-start gap-3 rounded-xl border p-3 text-sm">
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
            disabled={checkout.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!plan || !acceptedBillingTerms || checkout.isPending}
          >
            {checkout.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Opening checkout…
              </>
            ) : (
              <>Continue to checkout</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
