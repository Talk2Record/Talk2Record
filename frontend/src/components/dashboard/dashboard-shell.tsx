"use client";

import type { ReactNode } from "react";
import { Sidebar } from "@/shared/layout/sidebar";
import { DashboardTopbar } from "@/components/dashboard/dashboard-topbar";
import { ImpersonationBanner } from "@/components/dashboard/impersonation-banner";
import { useNotifications } from "@/shared/hooks/use-notifications";
import { AuthGate } from "@/shared/components/auth-gate";
import { LegalGate } from "@/shared/components/legal-gate";
import { UsageWarningBanner } from "@/components/billing/usage-warning-banner";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <LegalGate>
        <DashboardShellInner>{children}</DashboardShellInner>
      </LegalGate>
    </AuthGate>
  );
}

/**
 * The inner shell only mounts once `AuthGate` has confirmed the user is
 * authenticated. Notifications are intentionally subscribed here so we never
 * open a WebSocket with a stale or missing token.
 */
function DashboardShellInner({ children }: { children: ReactNode }) {
  useNotifications();

  return (
    <div className="bg-muted/20 flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <ImpersonationBanner />
        <DashboardTopbar />
        <UsageWarningBanner />
        <main className="flex-1 overflow-y-auto px-4 py-6 pt-20 md:px-8 md:pt-6">{children}</main>
      </div>
    </div>
  );
}
