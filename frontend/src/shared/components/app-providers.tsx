"use client";

import type { ReactNode } from "react";
import { useState, useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@/lib/query-client";
import { ThemeProvider } from "@/shared/components/theme-provider";
import { AuthProvider } from "@/shared/lib/auth/auth-context";
import { LanguageProvider } from "@/shared/lib/i18n/language-context";
import { initAnalytics } from "@/lib/analytics";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);

  useEffect(() => {
    initAnalytics();
  }, []);

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        <LanguageProvider>
          <AuthProvider>{children}</AuthProvider>
        </LanguageProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
