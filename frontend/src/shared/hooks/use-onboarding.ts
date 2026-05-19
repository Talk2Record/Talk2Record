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
  /** Required steps still pending. */
  pendingRequiredSteps: OnboardingStep[];
  /** True when every step is complete. */
  allStepsComplete: boolean;
  /** True when all required steps are complete (unlocks final attestations). */
  requiredStepsComplete: boolean;
}

/**
 * Single source of truth for the onboarding state machine. Mirrors the
 * backend's view of which steps are complete and combines it with the legal
 * status so the dashboard can decide whether to render the persistent
 * onboarding card.
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
  const requiredSteps = steps.filter((step) => step.required);
  const pendingRequiredSteps = requiredSteps.filter((step) => !step.completed);
  const allStepsComplete = steps.length > 0 && pendingSteps.length === 0;
  const requiredStepsComplete = requiredSteps.length > 0 && pendingRequiredSteps.length === 0;

  let status: OnboardingStatus;
  if (!legal.isSignupCompliant) {
    status = "legal-required";
  } else if (user?.onboardingCompleted) {
    status = "complete";
  } else if (requiredStepsComplete) {
    status = "ready-to-finalize";
  } else {
    status = "steps-pending";
  }

  return {
    steps,
    isLoading: stepsQuery.isLoading || legal.isLoading,
    status,
    pendingSteps,
    pendingRequiredSteps,
    allStepsComplete,
    requiredStepsComplete,
  };
}
