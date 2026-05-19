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
import { notifyApiError } from "@/shared/lib/notify-api-error";
import { trackEvent } from "@/lib/analytics";
import { useAuth } from "@/shared/lib/auth/auth-context";

interface PlanOption {
  code: string;
  name: string;
  priceLabel: string;
  description: string;
}

interface CheckoutConfirmModalProps {
  open: boolean;
  plan: PlanOption | null;
  onOpenChange: (_open: boolean) => void;
}

/**
 * Modal that confirms a plan + billing-terms acceptance before redirecting
 * the browser to the Paddle-hosted checkout. Reuses the existing
 * `billingService.checkout` mutation but adds:
 *
 *   - a real billing-terms checkbox (the API enforces this; without it the
 *     server returns 400)
 *   - per-mutation loading + error UX
 *   - analytics event symmetry with the old in-page button
 */
export function CheckoutConfirmModal({ open, plan, onOpenChange }: CheckoutConfirmModalProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [acceptedBillingTerms, setAcceptedBillingTerms] = useState(
    user?.legal?.has_required_billing_acceptance ?? false
  );

  const checkout = useMutation({
    mutationFn: (planCode: string) =>
      billingService.checkout({ plan: planCode, acceptedBillingTerms }),
    onSuccess: (response, planCode) => {
      trackEvent("billing_checkout_redirected", { plan: planCode });
      void queryClient.invalidateQueries({ queryKey: ["billing"] });
      if (response.checkoutUrl) {
        window.location.assign(response.checkoutUrl);
        return;
      }
      onOpenChange(false);
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
          <DialogDescription>{plan?.description}</DialogDescription>
        </DialogHeader>

        <div className="border-border bg-muted/30 mt-4 rounded-xl border p-4">
          <div className="flex items-baseline justify-between">
            <p className="text-sm font-medium">Plan price</p>
            <p className="text-2xl font-semibold">{plan?.priceLabel}</p>
          </div>
          <p className="text-muted-foreground mt-1 text-xs">
            You will be redirected to Paddle to complete payment securely.
          </p>
        </div>

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
