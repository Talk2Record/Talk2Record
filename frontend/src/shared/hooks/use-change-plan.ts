"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { billingService, PLANS_QUERY_KEY } from "@/services/platform-service";
import { BILLING_SNAPSHOT_QUERY_KEY } from "@/shared/hooks/use-usage";
import { openPaddleCheckout } from "@/shared/hooks/use-paddle-checkout";
import { notifyApiError } from "@/shared/lib/notify-api-error";
import { toast } from "@/shared/hooks/use-toast";
import type { ChangePlanResponse } from "@/types/platform";

export function useChangePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      plan: string;
      acceptedBillingTerms: boolean;
      successUrl?: string;
    }) => billingService.changePlan(payload),
    onError: (error) => notifyApiError(error, { title: "Could not update plan" }),
  });
}

export async function handleChangePlanSuccess(
  response: ChangePlanResponse,
  options: { onClose?: () => void; successUrl?: string } = {}
) {
  const needsCheckout =
    response.status === "checkout_required" ||
    response.status === "created" ||
    Boolean(response.transactionId || response.checkoutUrl);

  if (needsCheckout && (response.transactionId || response.checkoutUrl)) {
    if (response.transactionId) {
      // Close any parent dialog first — Radix modal overlays block Paddle iframe input.
      options.onClose?.();
      await new Promise<void>((resolve) => {
        window.setTimeout(resolve, 200);
      });

      const opened = await openPaddleCheckout({
        transactionId: response.transactionId,
        successUrl: options.successUrl,
      });
      if (opened) {
        return;
      }
    }

    if (response.checkoutUrl) {
      window.location.assign(response.checkoutUrl);
      return;
    }
  }

  toast({
    title: "Plan updated",
    description: "Your subscription has been changed. It may take a moment to reflect everywhere.",
  });
  options.onClose?.();
}

export function invalidateBillingQueries(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: BILLING_SNAPSHOT_QUERY_KEY });
  void queryClient.invalidateQueries({ queryKey: ["billing"] });
  void queryClient.invalidateQueries({ queryKey: PLANS_QUERY_KEY });
  void queryClient.invalidateQueries({ queryKey: ["billing", "entitlements"] });
  void queryClient.invalidateQueries({ queryKey: ["billing", "subscriptions"] });
}
