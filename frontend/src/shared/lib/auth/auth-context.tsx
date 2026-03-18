"use client";

import type React from "react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { AuthContext as AuthContextType } from "@/shared/lib/auth/types";
import { authService } from "@/services/platform-service";
import { useAuthStore } from "@/store/auth-store";
import { trackEvent } from "@/lib/analytics";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const setUser = useAuthStore((state) => state.setUser);
  const [isLoading, setIsLoading] = useState(false);
  const isAuthLoading = isLoading || !hasHydrated;

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      try {
        const nextUser = await authService.login(email, password);
        setUser(nextUser);
        trackEvent("auth_login", { emailDomain: email.split("@")[1] });
        return nextUser;
      } finally {
        setIsLoading(false);
      }
    },
    [setUser]
  );

  const register = useCallback(
    async (payload: { name: string; company: string; email: string; password: string }) => {
      setIsLoading(true);
      try {
        const nextUser = await authService.register(payload);
        setUser(nextUser);
        trackEvent("auth_register", { company: payload.company });
        return nextUser;
      } finally {
        setIsLoading(false);
      }
    },
    [setUser]
  );

  const requestPasswordReset = useCallback(async (email: string) => {
    setIsLoading(true);
    try {
      return await authService.forgotPassword(email);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const completeOnboarding = useCallback(async () => {
    if (!user) {
      return;
    }

    setIsLoading(true);
    try {
      const nextUser = await authService.completeOnboarding(user.id);
      setUser(nextUser);
      trackEvent("onboarding_completed", { userId: nextUser.id });
    } finally {
      setIsLoading(false);
    }
  }, [setUser, user]);

  const logout = useCallback(() => {
    setUser(null);
  }, [setUser]);

  const signInWithGoogle = useCallback(async () => {
    setIsLoading(true);
    try {
      const nextUser = await authService.loginWithGoogle();
      setUser(nextUser);
      trackEvent("auth_google_login");
    } finally {
      setIsLoading(false);
    }
  }, [setUser]);

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
      isGoogleEnabled: true,
    }),
    [
      completeOnboarding,
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
