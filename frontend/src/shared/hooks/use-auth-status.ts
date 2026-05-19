"use client";

import { useMemo } from "react";
import { useAuthStore } from "@/store/auth-store";
import { useImpersonationStore } from "@/store/impersonation-store";
import type { AuthUser } from "@/types/platform";

/**
 * Discriminated union describing every observable auth state in the app.
 * Consumers should switch on `kind` rather than juggling multiple booleans.
 *
 *   - booting          → store has not yet rehydrated from localStorage
 *   - anonymous        → no refresh token: user is logged out
 *   - resuming         → refresh token exists; we are loading /auth/me
 *   - authenticated    → user is loaded and tokens are present
 *   - expired          → last refresh failed; we're about to redirect to /login
 */
export type AuthStatus =
  | { kind: "booting" }
  | { kind: "anonymous" }
  | { kind: "resuming" }
  | { kind: "authenticated"; user: AuthUser }
  | { kind: "expired" };

export interface UseAuthStatusOptions {
  /**
   * True while React Query is fetching `/auth/me/` for the first time.
   * Passed in by `AuthProvider` (which owns the query) so we don't double-fetch.
   */
  isFetchingMe?: boolean;
  /** True if the last `/auth/me/` attempt errored after a refresh. */
  hadAuthError?: boolean;
}

export function useAuthStatus(options: UseAuthStatusOptions = {}): AuthStatus {
  const { isFetchingMe = false, hadAuthError = false } = options;
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const user = useAuthStore((state) => state.user);
  const accessToken = useAuthStore((state) => state.accessToken);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const isImpersonating = useImpersonationStore((state) => Boolean(state.active));

  return useMemo<AuthStatus>(() => {
    if (!hasHydrated) return { kind: "booting" };
    // Impersonation uses an access-only token (the backend issues no refresh
    // for safety), so we accept "access token + user" as authenticated when
    // an impersonation session is active. The banner takes over from there.
    if (isImpersonating && accessToken && user) {
      return { kind: "authenticated", user };
    }
    if (!refreshToken) return { kind: "anonymous" };
    if (hadAuthError) return { kind: "expired" };
    if (!user) {
      return isFetchingMe ? { kind: "resuming" } : { kind: "anonymous" };
    }
    return { kind: "authenticated", user };
  }, [hasHydrated, isImpersonating, accessToken, refreshToken, user, isFetchingMe, hadAuthError]);
}
