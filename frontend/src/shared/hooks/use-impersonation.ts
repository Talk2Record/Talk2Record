"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { adminUsersService } from "@/services/team-service";
import { authService } from "@/services/platform-service";
import { decodeAccessExpiry, useAuthStore } from "@/store/auth-store";
import {
  useImpersonationStore,
  type ActiveImpersonation,
  type ImpersonatorSnapshot,
} from "@/store/impersonation-store";
import { useOrgStore } from "@/store/org-store";
import { toast } from "@/shared/hooks/use-toast";
import { notifyApiError } from "@/shared/lib/notify-api-error";
import type { AdminUserRow, AuthUser } from "@/types/platform";

const IMPERSONATION_TTL_MS = 15 * 60 * 1000;

function snapshotAuthState(): ImpersonatorSnapshot | null {
  const { user, accessToken, refreshToken, accessExpiresAt } = useAuthStore.getState();
  if (!user || !accessToken || !refreshToken) return null;
  return {
    userId: user.id,
    email: user.email,
    accessToken,
    refreshToken,
    accessExpiresAt: accessExpiresAt ?? null,
  };
}

function adminRowToAuthUser(row: AdminUserRow): AuthUser {
  return {
    id: String(row.id),
    email: row.email,
    name: row.name || row.email,
    company: "",
    role: "admin",
    onboardingCompleted: row.onboarding_completed,
    isStaff: row.is_staff,
    isSuperuser: row.is_superuser,
    legal: {
      accepted_documents: [],
      required_signup_documents: [],
      required_billing_documents: [],
      has_required_signup_acceptance: true,
      has_required_billing_acceptance: true,
    },
  };
}

/**
 * Imperative helpers around the impersonation lifecycle:
 *
 *   - `startImpersonation(user)` snapshots the current session, calls the
 *     admin impersonate endpoint, swaps tokens in auth-store with the
 *     access-only impersonation token, records the start time, and clears
 *     org and query caches so the dashboard repaints under the target user.
 *
 *   - `stopImpersonation()` restores the snapshot, refetches `/auth/me/`,
 *     and clears the impersonation marker. We keep things idempotent so a
 *     reload mid-session lands on the original user thanks to the persisted
 *     snapshot.
 */
export function useImpersonationSession() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const active = useImpersonationStore((state) => state.active);
  const setActive = useImpersonationStore((state) => state.setActive);

  const startImpersonation = useCallback(
    async (targetRow: AdminUserRow) => {
      const original = snapshotAuthState();
      if (!original) {
        toast({
          title: "Cannot impersonate",
          description: "No active session to back up. Sign in again first.",
          variant: "destructive",
        });
        return;
      }
      try {
        const result = await adminUsersService.impersonate(targetRow.id);
        const fakeUser = adminRowToAuthUser(result.user);
        const newAccessExpiresAt = decodeAccessExpiry(result.access);

        const record: ActiveImpersonation = {
          targetUserId: String(result.user.id),
          targetEmail: result.user.email,
          startedAt: Date.now(),
          expiresAt: Date.now() + (result.expiresInSeconds ?? 15 * 60) * 1000,
          original,
        };

        // Swap session: replace tokens with the access-only impersonation
        // token. The persisted store already lives in localStorage so the
        // snapshot survives a refresh.
        useAuthStore.setState({
          user: fakeUser,
          accessToken: result.access,
          // Backend issues no refresh token for impersonation; clearing it
          // prevents the silent refresh scheduler from trying to use the
          // operator's refresh against the impersonated user's session.
          refreshToken: null,
          accessExpiresAt: newAccessExpiresAt,
        });
        // Reset org selection so the active org belongs to the impersonated
        // user, not the operator.
        useOrgStore.getState().setActiveOrg(null);
        setActive(record);
        queryClient.clear();

        toast({
          title: `Impersonating ${result.user.email}`,
          description: "You'll be returned to your own session in 15 minutes.",
        });
        router.replace("/dashboard");
      } catch (error) {
        notifyApiError(error, { title: "Impersonate failed" });
      }
    },
    [queryClient, router, setActive]
  );

  const stopImpersonation = useCallback(
    async (options: { reason?: "manual" | "expired" } = {}) => {
      const record = useImpersonationStore.getState().active;
      if (!record) return;

      // Restore the original session. Once tokens flip back the next call to
      // `/auth/me/` will produce a fresh user.
      useAuthStore.setState({
        user: null,
        accessToken: record.original.accessToken,
        refreshToken: record.original.refreshToken,
        accessExpiresAt: record.original.accessExpiresAt,
      });
      useOrgStore.getState().setActiveOrg(null);
      setActive(null);
      queryClient.clear();

      try {
        const me = await authService.getCurrentUser();
        useAuthStore.getState().setUser(me);
        queryClient.setQueryData(["auth", "me"], me);
      } catch {
        // If `/auth/me/` fails we let the standard auth machinery push the
        // operator to /login with a `reason=expired` parameter.
      }

      toast({
        title: options.reason === "expired" ? "Impersonation expired" : "Impersonation ended",
        description: `You're back as ${record.original.email}.`,
      });
      router.replace("/dashboard/admin/users");
    },
    [queryClient, router, setActive]
  );

  return { active, startImpersonation, stopImpersonation };
}

export const IMPERSONATION_TTL_MS_EXPORTED = IMPERSONATION_TTL_MS;
