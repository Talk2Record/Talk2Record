import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { AuthUser } from "@/types/platform";

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  hasHydrated: boolean;
  setUser: (_user: AuthUser | null) => void;
  setTokens: (_tokens: { accessToken: string | null; refreshToken: string | null }) => void;
  setSession: (_session: { user: AuthUser; accessToken: string; refreshToken: string }) => void;
  clearSession: () => void;
  setHasHydrated: (_hasHydrated: boolean) => void;
  updateUser: (_updates: Partial<AuthUser>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      hasHydrated: false,
      setUser: (user) => set({ user }),
      setTokens: ({ accessToken, refreshToken }) => set({ accessToken, refreshToken }),
      setSession: ({ user, accessToken, refreshToken }) => set({ user, accessToken, refreshToken }),
      clearSession: () => set({ user: null, accessToken: null, refreshToken: null }),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),
    }),
    {
      name: "talk2record-auth",
      storage: createJSONStorage(() => sessionStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
