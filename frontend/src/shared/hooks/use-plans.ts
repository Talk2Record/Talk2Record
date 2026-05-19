"use client";

import { useQuery } from "@tanstack/react-query";

import { billingService, PLANS_QUERY_KEY } from "@/services/platform-service";
import { usePreferencesStore } from "@/store/preferences-store";

export function usePlans() {
  const currency = usePreferencesStore((state) => state.currency);

  const query = useQuery({
    queryKey: [...PLANS_QUERY_KEY, currency],
    queryFn: () => billingService.listPlans(currency),
    staleTime: 5 * 60_000,
  });

  return {
    plans: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
