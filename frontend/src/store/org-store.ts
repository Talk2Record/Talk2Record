"use client";

import { create } from "zustand";
import { persist, createJSONStorage, type StateStorage } from "zustand/middleware";

/**
 * Holds the currently selected organization id for the active session.
 *
 * The backend resolves the operative org from the JWT `org_id` claim today,
 * so the front-end can't truly "switch tenants" without re-issuing the access
 * token. We still persist the user's choice in localStorage and surface it as
 * `X-Org-Id` on every API call. When the backend grows a header-driven switch
 * the wire is already in place. Until then, switching:
 *
 *   1. Updates the persisted `activeOrgId` so reloads keep the pick.
 *   2. Clears `["organizations:scoped", …]` query data so org-scoped data
 *      re-fetches against the new id.
 */
interface OrgState {
  activeOrgId: number | null;
  activeOrgSlug: string | null;
  hasHydrated: boolean;
  setActiveOrg: (_org: { id: number; slug?: string | null } | null) => void;
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

export const useOrgStore = create<OrgState>()(
  persist(
    (set) => ({
      activeOrgId: null,
      activeOrgSlug: null,
      hasHydrated: false,
      setActiveOrg: (org) =>
        set({
          activeOrgId: org?.id ?? null,
          activeOrgSlug: org?.slug ?? null,
        }),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
    }),
    {
      name: "talk2record-org",
      storage: createJSONStorage(() => safeLocalStorage),
      partialize: (state) => ({
        activeOrgId: state.activeOrgId,
        activeOrgSlug: state.activeOrgSlug,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

/**
 * Convenience reader for code paths outside of React (axios interceptor,
 * websocket reconnect, etc.).
 */
export function getActiveOrgId(): number | null {
  return useOrgStore.getState().activeOrgId;
}
