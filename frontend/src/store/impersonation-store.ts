"use client";

import { create } from "zustand";
import { persist, createJSONStorage, type StateStorage } from "zustand/middleware";

/**
 * The backend's `/admin/users/<id>/impersonate/` endpoint returns an
 * access-only token with a 15-minute lifetime — no refresh token is issued.
 * To keep the rest of the app working we:
 *
 *   1. Snapshot the original session (user, access, refresh, expiry) so we
 *      can restore it on exit or page reload after the impersonation token
 *      naturally expires.
 *   2. Drop the snapshot in localStorage so an accidental refresh doesn't
 *      strand the operator inside the impersonated tenant.
 */
export interface ImpersonatorSnapshot {
  userId: string;
  email: string;
  accessToken: string;
  refreshToken: string;
  accessExpiresAt: number | null;
}

export interface ActiveImpersonation {
  targetUserId: string;
  targetEmail: string;
  startedAt: number;
  /** UNIX-ms when the impersonation access token expires (~15 minutes). */
  expiresAt: number;
  /** Snapshot used to restore the original session. */
  original: ImpersonatorSnapshot;
}

interface ImpersonationState {
  active: ActiveImpersonation | null;
  hasHydrated: boolean;
  setActive: (_active: ActiveImpersonation | null) => void;
  setHasHydrated: (_value: boolean) => void;
}

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

export const useImpersonationStore = create<ImpersonationState>()(
  persist(
    (set) => ({
      active: null,
      hasHydrated: false,
      setActive: (active) => set({ active }),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
    }),
    {
      name: "talk2record-impersonation",
      storage: createJSONStorage(() => safeLocalStorage),
      partialize: (state) => ({ active: state.active }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
