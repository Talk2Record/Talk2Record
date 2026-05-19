"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AUTH_LOGOUT_EVENT } from "@/lib/api";
import { attachCrossTabAuthSync, useAuthStore } from "@/store/auth-store";
import { useImpersonationStore } from "@/store/impersonation-store";
import { authService } from "@/services/platform-service";
import { AUTH_ME_QUERY_KEY } from "@/shared/lib/auth/auth-context";
import { toast } from "@/shared/hooks/use-toast";

/**
 * Mounted once near the app root. Bridges three signals into the router:
 *
 *   1. axios → `talk2record:auth:logout` events fired when a refresh fails or
 *      a 401 is unrecoverable. Redirect to /login?reason=…
 *
 *   2. Cross-tab login: when another tab logs in, refetch /auth/me here so
 *      the dashboard appears without a manual reload.
 *
 *   3. Cross-tab logout: when another tab clears the session, clear query
 *      cache and (if we're on a dashboard page) bounce to /login.
 */
export function AuthEventListener() {
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    async function handleLogoutEvent(event: Event) {
      const detail = (event as CustomEvent<{ reason?: string }>).detail;
      const reason = detail?.reason || "expired";

      // If we logged out while impersonating, the impersonation token simply
      // expired or was rejected. Restore the original session rather than
      // bouncing the operator to /login.
      const impersonation = useImpersonationStore.getState().active;
      if (impersonation) {
        useAuthStore.setState({
          user: null,
          accessToken: impersonation.original.accessToken,
          refreshToken: impersonation.original.refreshToken,
          accessExpiresAt: impersonation.original.accessExpiresAt,
        });
        useImpersonationStore.getState().setActive(null);
        queryClient.clear();
        toast({
          title: "Impersonation ended",
          description: `You're back as ${impersonation.original.email}.`,
        });
        try {
          const me = await authService.getCurrentUser();
          useAuthStore.getState().setUser(me);
          queryClient.setQueryData(AUTH_ME_QUERY_KEY, me);
        } catch {
          // Fall through to the standard expired-session flow below.
        }
        if (useAuthStore.getState().refreshToken) {
          router.replace("/dashboard/admin/users");
          return;
        }
      }

      queryClient.clear();

      if (typeof window === "undefined") return;
      const path = window.location.pathname;
      if (path.startsWith("/dashboard") || path.startsWith("/onboarding")) {
        router.replace(`/login?reason=${reason}`);
      }
    }

    const onLogout = (event: Event) => {
      void handleLogoutEvent(event);
    };
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);

    const detachCrossTab = attachCrossTabAuthSync(() => {
      const { user, refreshToken } = useAuthStore.getState();
      if (!refreshToken) {
        queryClient.clear();
        if (typeof window !== "undefined" && window.location.pathname.startsWith("/dashboard")) {
          router.replace("/login");
        }
        return;
      }
      if (user) {
        queryClient.setQueryData(AUTH_ME_QUERY_KEY, user);
      }
      void queryClient.invalidateQueries({ queryKey: AUTH_ME_QUERY_KEY });
    });

    return () => {
      window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
      detachCrossTab();
    };
  }, [router, queryClient]);

  return null;
}
