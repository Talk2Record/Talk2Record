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
import { ErrorBoundary } from "@/shared/components/error-boundary";
import { AuthEventListener } from "@/shared/components/auth-event-listener";
import { isGoogleSignInEnabled } from "@/shared/lib/auth/google-auth-flag";

const isGoogleWorkspaceOAuthStackEnabled = isGoogleSignInEnabled();

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);

  useEffect(() => {
    initAnalytics();
  }, []);

  const core = (
    <LanguageProvider>
      <AuthProvider>
        <AuthEventListener />
        {children}
        <Toaster />
      </AuthProvider>
    </LanguageProvider>
  );

  return (
    <ErrorBoundary>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        <QueryClientProvider client={queryClient}>
          {isGoogleWorkspaceOAuthStackEnabled ? <SessionProvider>{core}</SessionProvider> : core}
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
