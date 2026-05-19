"use client";

import { useQuery } from "@tanstack/react-query";

import { legalService } from "@/services/platform-service";
import { useAuthStore } from "@/store/auth-store";
import type { LegalAcceptanceStatus } from "@/types/platform";

export const LEGAL_STATUS_QUERY_KEY = ["legal", "status"] as const;

export interface LegalStatusResult {
  status: LegalAcceptanceStatus | undefined;
  isLoading: boolean;
  /** Documents that are required at signup but the user has not yet accepted. */
  missingSignup: string[];
  /** Documents the user must accept before checkout. */
  missingBilling: string[];
  /** True only once we know the user is fully compliant for sign-up flows. */
  isSignupCompliant: boolean;
}

/**
 * React Query wrapper around `/legal/profile/status/`. Used by `<LegalGate />`,
 * the onboarding stepper, and the billing checkout flow.
 */
export function useLegalStatus(): LegalStatusResult {
  const refreshToken = useAuthStore((state) => state.refreshToken);

  const query = useQuery({
    queryKey: LEGAL_STATUS_QUERY_KEY,
    queryFn: legalService.getStatus,
    enabled: Boolean(refreshToken),
    staleTime: 5 * 60_000,
  });

  const status = query.data;
  const acceptedKeys = new Set(
    (status?.accepted_documents ?? []).filter((doc) => doc.acceptedAt).map((doc) => doc.documentKey)
  );

  const missingSignup = (status?.required_signup_documents ?? []).filter(
    (key) => !acceptedKeys.has(key)
  );
  const missingBilling = (status?.required_billing_documents ?? []).filter(
    (key) => !acceptedKeys.has(key)
  );

  return {
    status,
    isLoading: query.isLoading,
    missingSignup,
    missingBilling,
    isSignupCompliant: Boolean(status?.has_required_signup_acceptance),
  };
}
