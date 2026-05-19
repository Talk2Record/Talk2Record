"use client";

import { useQuery } from "@tanstack/react-query";

import { billingService } from "@/services/platform-service";
import { useAuthStore } from "@/store/auth-store";

/**
 * Matches the existing key used in `app/dashboard/billing/page.tsx` so all
 * usage/billing reads share a single cache entry and refetch together.
 */
export const BILLING_SNAPSHOT_QUERY_KEY = ["billing"] as const;

export type UsageState = "ok" | "approaching" | "exceeded";

export interface UsageSummary {
  processed: number;
  included: number;
  ratio: number;
  /** Discrete tier used to drive banners and progress bar colors. */
  state: UsageState;
  renewalDate: string | null;
  isLoading: boolean;
}

/**
 * Single read of the user's voice-note quota for the current billing cycle.
 * Backed by `/api/billing/` (the canonical billing snapshot). When the
 * backend ever exposes a richer usage endpoint we can swap the implementation
 * here without touching any consumer.
 */
export function useUsage(): UsageSummary {
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const query = useQuery({
    queryKey: BILLING_SNAPSHOT_QUERY_KEY,
    queryFn: billingService.getSnapshot,
    enabled: Boolean(refreshToken),
    staleTime: 60_000,
  });

  const sub = query.data?.subscription;
  const processed = sub?.voiceNotesProcessed ?? 0;
  const included = sub?.includedVoiceNotes ?? 0;
  const ratio = included > 0 ? processed / included : 0;

  let state: UsageState;
  if (ratio >= 1) state = "exceeded";
  else if (ratio >= 0.7) state = "approaching";
  else state = "ok";

  return {
    processed,
    included,
    ratio,
    state,
    renewalDate: sub?.renewalDate ?? null,
    isLoading: query.isLoading,
  };
}
