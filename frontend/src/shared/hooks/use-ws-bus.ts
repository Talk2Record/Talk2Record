"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { wsBus, deriveWsBaseUrl, type WsConnectionStatus } from "@/lib/ws-bus";

function getApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return baseUrl.replace(/\/$/, "");
}

/**
 * Singleton bus lifecycle:
 *   - mount once (DashboardShell) — opens a socket with the current access token
 *   - if the access token rotates (silent refresh) — replace and reopen
 *   - on logout / no token — disconnect
 *
 * The bus itself manages reconnect, so this hook only mirrors auth into it.
 */
export function useWsBusLifecycle() {
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!accessToken) {
      wsBus.disconnect();
      return;
    }
    const wsBaseUrl = deriveWsBaseUrl(getApiBaseUrl());
    wsBus.connect(wsBaseUrl, accessToken);
    // If accessToken changes between renders the next effect run handles it.
  }, [accessToken]);

  // On token rotation (silent refresh) the previous effect closure already
  // saw the new token. But we also keep an explicit replace path so the
  // hook reads as the source of truth even if the bus is already open.
  useEffect(() => {
    if (!accessToken) return;
    wsBus.replace(accessToken);
  }, [accessToken]);
}

/**
 * Read the current WS connection status as React state. Returns `"idle"`
 * when nothing has connected yet, useful for a "Live" topbar dot.
 */
export function useWsConnectionStatus(): WsConnectionStatus {
  const [status, setStatus] = useState<WsConnectionStatus>(wsBus.status);
  useEffect(() => wsBus.onStatusChange(setStatus), []);
  return status;
}
