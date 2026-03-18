"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/shared/layout/sidebar";
import { DashboardTopbar } from "@/components/dashboard/dashboard-topbar";
import { useAuth } from "@/shared/lib/auth/auth-context";

export function DashboardShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30">
        <div className="brand-panel rounded-3xl border border-primary/10 px-6 py-5 text-center">
          <p className="text-lg font-semibold">Loading workspace...</p>
          <p className="text-muted-foreground mt-1 text-sm">Preparing your Talk2Record intelligence workspace.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-muted/20">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <DashboardTopbar />
        <main className="flex-1 px-4 py-6 pt-20 md:px-8 md:pt-6">{children}</main>
      </div>
    </div>
  );
}
