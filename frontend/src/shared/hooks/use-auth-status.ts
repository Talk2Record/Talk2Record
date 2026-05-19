"use client";

import { useMemo } from "react";
import { useAuthStore } from "@/store/auth-store";
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
  const refreshToken = useAuthStore((state) => state.refreshToken);

  return useMemo<AuthStatus>(() => {
    if (!hasHydrated) return { kind: "booting" };
    if (!refreshToken) return { kind: "anonymous" };
    if (hadAuthError) return { kind: "expired" };
    if (!user) {
      return isFetchingMe ? { kind: "resuming" } : { kind: "anonymous" };
    }
    return { kind: "authenticated", user };
  }, [hasHydrated, refreshToken, user, isFetchingMe, hadAuthError]);
}
