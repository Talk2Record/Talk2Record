"use client";

import type React from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { AuthContext as AuthContextType } from "@/shared/lib/auth/types";
import { authService } from "@/services/platform-service";
import { useAuthStore } from "@/store/auth-store";
import { useAuthStatus } from "@/shared/hooks/use-auth-status";
import { useSilentRefresh } from "@/shared/hooks/use-silent-refresh";
import { trackEvent } from "@/lib/analytics";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Query key for the canonical "current user" fetch. Mutations that change
 * profile fields should `queryClient.setQueryData(AUTH_ME_QUERY_KEY, …)` AND
 * mirror into the Zustand store via `updateUser`.
 */
export const AUTH_ME_QUERY_KEY = ["auth", "me"] as const;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const setSession = useAuthStore((state) => state.setSession);
  const setUser = useAuthStore((state) => state.setUser);
  const clearSession = useAuthStore((state) => state.clearSession);
  const [isMutating, setIsMutating] = useState(false);

  useSilentRefresh();

  const meQuery = useQuery({
    queryKey: AUTH_ME_QUERY_KEY,
    queryFn: authService.getCurrentUser,
    enabled: hasHydrated && Boolean(refreshToken),
    staleTime: 5 * 60_000,
    retry: 0,
  });

  /**
   * Mirror the React Query result into the Zustand store so synchronous reads
   * (sidebar, guards) still work without a hook.
   */
  useEffect(() => {
    if (meQuery.data) {
      setUser(meQuery.data);
    }
  }, [meQuery.data, setUser]);

  /**
   * If `/auth/me/` fails after the axios interceptor has already attempted a
   * refresh, the session is unrecoverable. Clear local state so the next
   * paint redirects to /login. We do this in an effect to avoid setState
   * during a render.
   */
  useEffect(() => {
    if (meQuery.isError && refreshToken) {
      clearSession();
      queryClient.removeQueries({ queryKey: AUTH_ME_QUERY_KEY });
    }
  }, [meQuery.isError, refreshToken, clearSession, queryClient]);

  /** NextAuth Google UI + SessionProvider only when OAuth is explicitly enabled end-to-end (see docs/AUTH.md). */
  const isGoogleEnabled =
    process.env.NEXT_PUBLIC_GOOGLE_AUTH_ENABLED === "true" &&
    process.env.NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN === "true";

  const status = useAuthStatus({
    isFetchingMe: meQuery.isFetching,
    hadAuthError: meQuery.isError && Boolean(refreshToken),
  });

  const isAuthLoading =
    isMutating || !hasHydrated || (Boolean(refreshToken) && !user && meQuery.isFetching);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsMutating(true);
      try {
        const session = await authService.login(email, password);
        setSession(session);
        queryClient.setQueryData(AUTH_ME_QUERY_KEY, session.user);
        trackEvent("auth_login", { emailDomain: email.split("@")[1] });
        return session.user;
      } finally {
        setIsMutating(false);
      }
    },
    [setSession, queryClient]
  );

  const register = useCallback(
    async (payload: {
      name: string;
      company: string;
      email: string;
      password: string;
      acceptedDocumentKeys: string[];
    }) => {
      setIsMutating(true);
      try {
        const session = await authService.register(payload);
        setSession(session);
        queryClient.setQueryData(AUTH_ME_QUERY_KEY, session.user);
        trackEvent("auth_register", { company: payload.company });
        return session.user;
      } finally {
        setIsMutating(false);
      }
    },
    [setSession, queryClient]
  );

  const requestPasswordReset = useCallback(async (email: string) => {
    setIsMutating(true);
    try {
      return await authService.forgotPassword(email);
    } finally {
      setIsMutating(false);
    }
  }, []);

  const completeOnboarding = useCallback(
    async (payload: {
      voiceDataConsent: boolean;
      aiReviewAcknowledged: boolean;
      recordVerificationAcknowledged: boolean;
    }) => {
      if (!user) {
        return;
      }

      setIsMutating(true);
      try {
        const nextUser = await authService.completeOnboarding(payload);
        setUser(nextUser);
        queryClient.setQueryData(AUTH_ME_QUERY_KEY, nextUser);
        trackEvent("onboarding_completed", { userId: nextUser.id });
      } finally {
        setIsMutating(false);
      }
    },
    [setUser, user, queryClient]
  );

  const logout = useCallback(async () => {
    setIsMutating(true);
    try {
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } catch {
      // Clearing local session keeps the client consistent even if the backend token is already expired.
    } finally {
      clearSession();
      queryClient.clear();
      setIsMutating(false);
    }
  }, [clearSession, refreshToken, queryClient]);

  const signInWithGoogle = useCallback(async () => {
    if (!isGoogleEnabled) {
      throw new Error("Google sign-in is not enabled for this environment.");
    }
    const { signIn } = await import("next-auth/react");
    await signIn("google", { callbackUrl: "/dashboard" });
  }, [isGoogleEnabled]);

  const value = useMemo(
    () => ({
      user,
      isLoading: isAuthLoading,
      status,
      login,
      register,
      requestPasswordReset,
      completeOnboarding,
      logout,
      signInWithGoogle,
      isAuthenticated: status.kind === "authenticated",
      isGoogleEnabled,
    }),
    [
      completeOnboarding,
      isGoogleEnabled,
      isAuthLoading,
      login,
      logout,
      register,
      requestPasswordReset,
      signInWithGoogle,
      status,
      user,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
