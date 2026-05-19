"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { Skeleton } from "@/shared/ui/skeleton";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useLegalStatus } from "@/shared/hooks/use-legal-status";

interface LegalGateProps {
  children: ReactNode;
}

/**
 * Blocks every dashboard page from rendering until the user has accepted the
 * required signup-time legal documents. Pushes the user to `/onboarding` so
 * they can complete the legal stepper. Settings remain reachable in case the
 * user needs to update their profile before continuing.
 *
 * We deliberately don't gate `/dashboard/settings` so users can finish their
 * profile if the legal acceptance got out of sync.
 */
export function LegalGate({ children }: LegalGateProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { status: authStatus } = useAuth();
  const { isLoading, isSignupCompliant, status } = useLegalStatus();

  const allowedWhileBlocked =
    pathname === "/dashboard/settings" || pathname?.startsWith("/dashboard/settings/");

  useEffect(() => {
    if (authStatus.kind !== "authenticated") return;
    if (isLoading || !status) return;
    if (isSignupCompliant) return;
    if (allowedWhileBlocked) return;
    if (pathname?.startsWith("/onboarding")) return;
    router.replace("/onboarding?reason=legal-required");
  }, [
    authStatus.kind,
    isLoading,
    isSignupCompliant,
    status,
    allowedWhileBlocked,
    pathname,
    router,
  ]);

  if (authStatus.kind !== "authenticated") return <>{children}</>;

  if (isLoading && !status) {
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    );
  }

  return <>{children}</>;
}
