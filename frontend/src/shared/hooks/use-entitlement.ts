"use client";

import { useQuery } from "@tanstack/react-query";
import { billingService, type EntitlementRow } from "@/services/platform-service";

export const BILLING_ENTITLEMENTS_QUERY_KEY = ["billing", "entitlements"] as const;

export interface EntitlementResult {
  enabled: boolean;
  limit: number;
  period: EntitlementRow["period"];
  /** True while the entitlement list is still loading (treat as enabled to avoid flicker). */
  isLoading: boolean;
  /** The raw row when found, undefined otherwise. */
  row: EntitlementRow | undefined;
}

/**
 * Read a single feature entitlement by its key. Components can use this to
 * soft-gate UI (locked card with upsell CTA) without hitting an API per gate.
 *
 *   const { enabled, limit } = useEntitlement("analytics.advanced");
 *   if (!enabled) return <UpgradeLock />;
 *
 * While the entitlements query is loading we report `enabled: true` so the
 * UI doesn't flash a "locked" state on first paint.
 */
export function useEntitlement(featureKey: string): EntitlementResult {
  const query = useQuery({
    queryKey: BILLING_ENTITLEMENTS_QUERY_KEY,
    queryFn: () => billingService.listEntitlements(),
  });

  const row = query.data?.find((r) => r.feature_key === featureKey);

  return {
    enabled: row ? row.enabled : true,
    limit: row?.limit ?? 0,
    period: row?.period ?? "none",
    isLoading: query.isLoading,
    row,
  };
}
