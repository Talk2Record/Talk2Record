"use client";

import { useEffect } from "react";
import axios from "axios";
import { useAuthStore, decodeAccessExpiry } from "@/store/auth-store";

const REFRESH_LEAD_TIME_MS = 60_000;
const MIN_DELAY_MS = 5_000;

/**
 * Proactively refresh the access token shortly before it expires so we never
 * lose an inflight WebSocket connection or trigger a noticeable 401 spike on
 * the user's next click.
 *
 * The scheduler:
 *   - runs only when both `accessExpiresAt` and `refreshToken` are present;
 *   - schedules a single timeout for `accessExpiresAt - REFRESH_LEAD_TIME_MS`;
 *   - reschedules whenever the access token rotates;
 *   - is idempotent: mount it once at the app root.
 */
export function useSilentRefresh() {
  const accessExpiresAt = useAuthStore((state) => state.accessExpiresAt);
  const refreshToken = useAuthStore((state) => state.refreshToken);

  useEffect(() => {
    if (!refreshToken || !accessExpiresAt) return;

    const delay = Math.max(MIN_DELAY_MS, accessExpiresAt - Date.now() - REFRESH_LEAD_TIME_MS);

    const timer = setTimeout(() => {
      void refreshAccessTokenInBackground();
    }, delay);

    return () => clearTimeout(timer);
  }, [accessExpiresAt, refreshToken]);
}

let inflight: Promise<void> | null = null;

async function refreshAccessTokenInBackground(): Promise<void> {
  if (inflight) return inflight;

  inflight = (async () => {
    const { refreshToken } = useAuthStore.getState();
    if (!refreshToken) return;

    const baseUrl = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

    try {
      const response = await axios.post<{ access: string }>(
        `${baseUrl}/auth/refresh/`,
        { refresh: refreshToken },
        { headers: { "Content-Type": "application/json" }, timeout: 10_000 }
      );
      useAuthStore.getState().setTokens({
        accessToken: response.data.access,
        refreshToken,
      });
      // setTokens recomputes accessExpiresAt; subscriber will reschedule.
      void decodeAccessExpiry; // keep the import explicit for tree-shaking sanity
    } catch {
      // Don't clear session on background failure — the next user-driven
      // request will trigger the 401 path which handles redirect + logout.
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}

function normalizeApiBaseUrl(value?: string) {
  const baseUrl = (value || "http://localhost:8000").replace(/\/$/, "");
  return baseUrl.endsWith("/api") ? baseUrl : `${baseUrl}/api`;
}
