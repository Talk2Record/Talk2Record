"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { buildLoginRedirect } from "@/shared/lib/auth/safe-redirect";
import { Skeleton } from "@/shared/ui/skeleton";

interface AuthGateProps {
  children: ReactNode;
  /**
   * Optional fallback while we wait for the auth machine to settle. Defaults
   * to a centered shell skeleton that matches the dashboard layout so the
   * transition between booting → authenticated is invisible.
   */
  fallback?: ReactNode;
}

/**
 * Single source of truth for "is this page allowed?" on authenticated routes.
 *
 *   - while the store is booting OR /auth/me is fetching → render fallback
 *   - if anonymous or expired → push to /login with current path as redirect
 *   - if authenticated → render children
 *
 * This replaces ad-hoc `if (!isAuthenticated) router.replace("/login")` checks
 * sprinkled across dashboard layouts so the redirect logic only lives here.
 */
export function AuthGate({ children, fallback }: AuthGateProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { status } = useAuth();

  useEffect(() => {
    if (status.kind === "anonymous" || status.kind === "expired") {
      const target = buildLoginRedirect(pathname ?? "/");
      const reason = status.kind === "expired" ? "expired" : undefined;
      const url = reason
        ? target.includes("?")
          ? `${target}&reason=${reason}`
          : `${target}?reason=${reason}`
        : target;
      router.replace(url);
    }
  }, [status.kind, pathname, router]);

  if (status.kind === "authenticated") {
    return <>{children}</>;
  }

  return <>{fallback ?? <AuthGateFallback />}</>;
}

function AuthGateFallback() {
  return (
    <div className="bg-muted/30 flex min-h-screen items-center justify-center px-4 py-10">
      <div className="brand-panel border-primary/10 w-full max-w-md space-y-4 rounded-3xl border p-8">
        <div className="space-y-2">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-2/3" />
        </div>
      </div>
    </div>
  );
}

/**
 * Companion to `AuthGate`: redirect already-authenticated users away from
 * pages that should only be shown when logged out (e.g. /login, /register).
 * If a `?redirect=` query is present and safe, it's honored.
 *
 * Do **not** wrap post-login flows (e.g. `/onboarding`) in this guard — it
 * returns `null` for authenticated users, which causes a blank page and a
 * redirect fight with `LegalGate`. Use `(onboarding)` + `AuthGate` instead.
 */
interface AuthRedirectGuardProps {
  children: ReactNode;
  defaultDestination?: string;
}

export function GuestOnly({ children, defaultDestination = "/dashboard" }: AuthRedirectGuardProps) {
  const router = useRouter();
  const { status } = useAuth();

  useEffect(() => {
    if (status.kind !== "authenticated") return;

    const params = new URLSearchParams(window.location.search);
    const redirect = params.get("redirect");
    const safe = redirect
      ? // Reuse sanitizer via dynamic import would create a cycle on the auth layout;
        // do the simple check inline.
        redirect.startsWith("/") && !redirect.startsWith("//")
        ? redirect
        : null
      : null;

    router.replace(safe ?? defaultDestination);
  }, [status.kind, router, defaultDestination]);

  if (status.kind === "authenticated") return null;
  return <>{children}</>;
}
