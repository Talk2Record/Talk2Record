"use client";

import { create } from "zustand";
import { persist, createJSONStorage, type StateStorage } from "zustand/middleware";
import type { AuthUser } from "@/types/platform";

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  /** Unix epoch milliseconds at which the current access token expires. */
  accessExpiresAt: number | null;
  /** True once zustand has finished reading the persisted blob from storage. */
  hasHydrated: boolean;
  setUser: (_user: AuthUser | null) => void;
  setTokens: (_tokens: { accessToken: string | null; refreshToken: string | null }) => void;
  setSession: (_session: { user: AuthUser; accessToken: string; refreshToken: string }) => void;
  clearSession: () => void;
  setHasHydrated: (_hasHydrated: boolean) => void;
  updateUser: (_updates: Partial<AuthUser>) => void;
}

/**
 * Decode a JWT `exp` claim into a UNIX epoch millisecond timestamp. We avoid
 * adding a JWT decode dependency: tokens are base64url-encoded and we only
 * need the `exp` field.
 *
 * Returns null when the token shape is invalid or `exp` is missing.
 */
export function decodeAccessExpiry(accessToken: string | null | undefined): number | null {
  if (!accessToken) return null;
  try {
    const parts = accessToken.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
    const decoded =
      typeof atob === "function" ? atob(padded) : Buffer.from(padded, "base64").toString("binary");
    const json = JSON.parse(decoded) as { exp?: number };
    if (typeof json.exp !== "number") return null;
    return json.exp * 1000;
  } catch {
    return null;
  }
}

/**
 * Multi-tab sync via BroadcastChannel with a localStorage event fallback.
 * When a user logs in or out in one tab, every other open tab learns about
 * it immediately and rehydrates its in-memory store from localStorage.
 */
const BROADCAST_NAME = "talk2record:auth";

type BroadcastMessage =
  | { type: "login"; tabId: string }
  | { type: "logout"; tabId: string }
  | { type: "update"; tabId: string };

let broadcastChannel: BroadcastChannel | null = null;
const TAB_ID =
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

function getBroadcastChannel(): BroadcastChannel | null {
  if (typeof window === "undefined") return null;
  if (typeof BroadcastChannel === "undefined") return null;
  if (!broadcastChannel) {
    broadcastChannel = new BroadcastChannel(BROADCAST_NAME);
  }
  return broadcastChannel;
}

function postBroadcast(message: BroadcastMessage) {
  const channel = getBroadcastChannel();
  if (channel) {
    channel.postMessage(message);
  }
}

/**
 * SSR-safe storage shim that returns the real localStorage on the client and
 * a no-op shape on the server. Prevents `localStorage is not defined` on the
 * first server render while still keeping the same JSON serialization.
 */
const safeLocalStorage: StateStorage = {
  getItem: (key) => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(key);
  },
  setItem: (key, value) => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(key, value);
  },
  removeItem: (key) => {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(key);
  },
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      accessExpiresAt: null,
      hasHydrated: false,
      setUser: (user) => {
        set({ user });
        postBroadcast({ type: "update", tabId: TAB_ID });
      },
      setTokens: ({ accessToken, refreshToken }) => {
        set({
          accessToken,
          refreshToken,
          accessExpiresAt: decodeAccessExpiry(accessToken),
        });
        postBroadcast({ type: "update", tabId: TAB_ID });
      },
      setSession: ({ user, accessToken, refreshToken }) => {
        set({
          user,
          accessToken,
          refreshToken,
          accessExpiresAt: decodeAccessExpiry(accessToken),
        });
        postBroadcast({ type: "login", tabId: TAB_ID });
      },
      clearSession: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          accessExpiresAt: null,
        });
        postBroadcast({ type: "logout", tabId: TAB_ID });
      },
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),
    }),
    {
      name: "talk2record-auth",
      storage: createJSONStorage(() => safeLocalStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        accessExpiresAt: state.accessExpiresAt,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

/**
 * Wire up cross-tab listeners. Called once from the client during app
 * bootstrap (see `AppProviders`). Safe to call multiple times — subsequent
 * calls are no-ops.
 */
let crossTabListenersAttached = false;

export function attachCrossTabAuthSync(onRemoteChange?: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  if (crossTabListenersAttached) return () => undefined;
  crossTabListenersAttached = true;

  const handleBroadcast = (event: MessageEvent<BroadcastMessage>) => {
    if (!event.data || event.data.tabId === TAB_ID) return;
    void useAuthStore.persist.rehydrate();
    onRemoteChange?.();
  };

  const handleStorage = (event: StorageEvent) => {
    if (event.key !== "talk2record-auth") return;
    void useAuthStore.persist.rehydrate();
    onRemoteChange?.();
  };

  const channel = getBroadcastChannel();
  channel?.addEventListener("message", handleBroadcast);
  window.addEventListener("storage", handleStorage);

  return () => {
    channel?.removeEventListener("message", handleBroadcast);
    window.removeEventListener("storage", handleStorage);
    crossTabListenersAttached = false;
  };
}
