"use client";

import { useQuery } from "@tanstack/react-query";

import { onboardingService } from "@/services/platform-service";
import { useAuthStore } from "@/store/auth-store";
import { useLegalStatus } from "@/shared/hooks/use-legal-status";
import type { OnboardingStep } from "@/types/platform";

export const ONBOARDING_STEPS_QUERY_KEY = ["onboarding", "steps"] as const;

export type OnboardingStatus =
  | "legal-required"
  | "steps-pending"
  | "ready-to-finalize"
  | "complete";

export interface OnboardingSnapshot {
  steps: OnboardingStep[];
  isLoading: boolean;
  status: OnboardingStatus;
  /** Steps the user still needs to satisfy server-side. */
  pendingSteps: OnboardingStep[];
  /** True when all backend steps are done so the user can finalize. */
  allStepsComplete: boolean;
}

/**
 * Single source of truth for the onboarding state machine. Mirrors the
 * backend's view of which steps are complete and combines it with the legal
 * status so the dashboard can decide whether to render the persistent
 * onboarding card.
 *
 * Steps are server-derived: connecting WhatsApp, processing a first voice
 * note, and completing the company setup checklist all flip server-side, so
 * the UI just reflects what the API says rather than guessing.
 */
export function useOnboardingSnapshot(): OnboardingSnapshot {
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const user = useAuthStore((state) => state.user);

  const stepsQuery = useQuery({
    queryKey: ONBOARDING_STEPS_QUERY_KEY,
    queryFn: () => onboardingService.getSteps(),
    enabled: Boolean(refreshToken),
    staleTime: 60_000,
  });

  const legal = useLegalStatus();

  const steps = stepsQuery.data ?? [];
  const pendingSteps = steps.filter((step) => !step.completed);
  const allStepsComplete = steps.length > 0 && pendingSteps.length === 0;

  let status: OnboardingStatus;
  if (!legal.isSignupCompliant) {
    status = "legal-required";
  } else if (user?.onboardingCompleted) {
    status = "complete";
  } else if (allStepsComplete) {
    status = "ready-to-finalize";
  } else {
    status = "steps-pending";
  }

  return {
    steps,
    isLoading: stepsQuery.isLoading || legal.isLoading,
    status,
    pendingSteps,
    allStepsComplete,
  };
}
