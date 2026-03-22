"use client";

import type { ReactNode } from "react";
import { useState, useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@/lib/query-client";
import { ThemeProvider } from "@/shared/components/theme-provider";
import { AuthProvider } from "@/shared/lib/auth/auth-context";
import { LanguageProvider } from "@/shared/lib/i18n/language-context";
import { SessionProvider } from "@/shared/lib/auth/session-provider";
import { initAnalytics } from "@/lib/analytics";
import { Toaster } from "@/shared/components/toaster";

const isGoogleWorkspaceOAuthStackEnabled =
  process.env.NEXT_PUBLIC_GOOGLE_AUTH_ENABLED === "true" &&
  process.env.NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN === "true";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);

  useEffect(() => {
    initAnalytics();
  }, []);

  const core = (
    <LanguageProvider>
      <AuthProvider>
        {children}
        <Toaster />
      </AuthProvider>
    </LanguageProvider>
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        {isGoogleWorkspaceOAuthStackEnabled ? <SessionProvider>{core}</SessionProvider> : core}
      </QueryClientProvider>
    </ThemeProvider>
  );
}
