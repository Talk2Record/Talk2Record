"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { organizationsService } from "@/services/platform-service";
import { useOrgStore } from "@/store/org-store";
import { useAuthStore } from "@/store/auth-store";
import type { OrganizationSummary } from "@/types/platform";

export const ORGANIZATIONS_QUERY_KEY = ["organizations"] as const;

/**
 * Reads the list of organizations the current user belongs to, and keeps the
 * persisted `activeOrgId` in sync:
 *
 *   - if no active org has been chosen yet, default to the first returned
 *     organization (matches the JWT-resolved tenant for new sessions);
 *   - if the persisted id is no longer present (membership revoked, org
 *     deleted), gracefully fall back to the first available org.
 */
export function useOrganizations() {
  const queryClient = useQueryClient();
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const activeOrgId = useOrgStore((state) => state.activeOrgId);
  const setActiveOrg = useOrgStore((state) => state.setActiveOrg);

  const query = useQuery({
    queryKey: ORGANIZATIONS_QUERY_KEY,
    queryFn: organizationsService.list,
    enabled: Boolean(refreshToken),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    const orgs = query.data;
    if (!orgs || orgs.length === 0) return;

    const stillPresent = activeOrgId && orgs.some((org) => org.id === activeOrgId);
    if (stillPresent) return;

    const next = orgs[0];
    setActiveOrg({ id: next.id, slug: next.slug });
    // The newly selected org may have different scoped data: drop any
    // org-scoped cache entries so consumers refetch under the new context.
    void queryClient.invalidateQueries({
      predicate: (q) =>
        Array.isArray(q.queryKey) && q.queryKey[0] !== "organizations" && q.queryKey[0] !== "auth",
    });
  }, [query.data, activeOrgId, setActiveOrg, queryClient]);

  return query;
}

/**
 * Returns the currently selected organization plus a `switchTo` helper. The
 * helper updates the persisted id and drops all org-scoped query caches so
 * the next render fetches under the new context.
 */
export function useActiveOrg() {
  const queryClient = useQueryClient();
  const activeOrgId = useOrgStore((state) => state.activeOrgId);
  const setActiveOrg = useOrgStore((state) => state.setActiveOrg);
  const { data: organizations = [] } = useOrganizations();

  const active: OrganizationSummary | null =
    organizations.find((org) => org.id === activeOrgId) ?? null;

  function switchTo(org: OrganizationSummary) {
    if (org.id === activeOrgId) return;
    setActiveOrg({ id: org.id, slug: org.slug });
    // Anything that isn't auth/org/preference data should re-fetch under the
    // new tenant; the predicate keeps it cheap by not removing those keys.
    void queryClient.invalidateQueries({
      predicate: (q) =>
        Array.isArray(q.queryKey) && q.queryKey[0] !== "organizations" && q.queryKey[0] !== "auth",
    });
  }

  return { active, organizations, switchTo };
}
