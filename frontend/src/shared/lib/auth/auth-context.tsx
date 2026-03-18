"use client";

import type React from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { AuthContext as AuthContextType } from "@/shared/lib/auth/types";
import { authService } from "@/services/platform-service";
import { useAuthStore } from "@/store/auth-store";
import { trackEvent } from "@/lib/analytics";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const setSession = useAuthStore((state) => state.setSession);
  const setUser = useAuthStore((state) => state.setUser);
  const clearSession = useAuthStore((state) => state.clearSession);
  const [isLoading, setIsLoading] = useState(false);
  const isAuthLoading = isLoading || !hasHydrated;
  const isGoogleEnabled = process.env.NEXT_PUBLIC_GOOGLE_AUTH_ENABLED === "true";

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    if (!refreshToken) {
      clearSession();
      return;
    }

    let isMounted = true;

    const syncCurrentUser = async () => {
      setIsLoading(true);
      try {
        const currentUser = await authService.getCurrentUser();
        if (isMounted) {
          setUser(currentUser);
        }
      } catch {
        if (isMounted) {
          clearSession();
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void syncCurrentUser();

    return () => {
      isMounted = false;
    };
  }, [clearSession, hasHydrated, refreshToken, setUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      try {
        const session = await authService.login(email, password);
        setSession(session);
        trackEvent("auth_login", { emailDomain: email.split("@")[1] });
        return session.user;
      } finally {
        setIsLoading(false);
      }
    },
    [setSession]
  );

  const register = useCallback(
    async (payload: {
      name: string;
      company: string;
      email: string;
      password: string;
      acceptedDocumentKeys: string[];
    }) => {
      setIsLoading(true);
      try {
        const session = await authService.register(payload);
        setSession(session);
        trackEvent("auth_register", { company: payload.company });
        return session.user;
      } finally {
        setIsLoading(false);
      }
    },
    [setSession]
  );

  const requestPasswordReset = useCallback(async (email: string) => {
    setIsLoading(true);
    try {
      return await authService.forgotPassword(email);
    } finally {
      setIsLoading(false);
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

      setIsLoading(true);
      try {
        const nextUser = await authService.completeOnboarding(payload);
        setUser(nextUser);
        trackEvent("onboarding_completed", { userId: nextUser.id });
      } finally {
        setIsLoading(false);
      }
    },
    [setUser, user]
  );

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } catch {
      // Clearing local session keeps the client consistent even if the backend token is already expired.
    } finally {
      clearSession();
      setIsLoading(false);
    }
  }, [clearSession, refreshToken]);

  const signInWithGoogle = useCallback(async () => {
    if (!isGoogleEnabled) {
      throw new Error("Google sign-in is not enabled for this environment.");
    }
  }, [isGoogleEnabled]);

  const value = useMemo(
    () => ({
      user,
      isLoading: isAuthLoading,
      login,
      register,
      requestPasswordReset,
      completeOnboarding,
      logout,
      signInWithGoogle,
      isAuthenticated: Boolean(user),
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
