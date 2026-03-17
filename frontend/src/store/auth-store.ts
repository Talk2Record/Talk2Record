import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { AuthUser } from "@/types/platform";

interface AuthState {
  user: AuthUser | null;
  setUser: (_user: AuthUser | null) => void;
  updateUser: (_updates: Partial<AuthUser>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),
    }),
    {
      name: "talk2record-auth",
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);
