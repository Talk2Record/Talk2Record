import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { resolveDefaultCurrency } from "@/lib/format";
import type { SupportedCurrency } from "@/types/platform";
import type { Locale } from "@/shared/lib/i18n/types";

interface PreferencesState {
  currency: SupportedCurrency;
  setCurrency: (_currency: SupportedCurrency) => void;
  localeOverride: Locale | null;
  setLocaleOverride: (_locale: Locale) => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      currency: resolveDefaultCurrency("en_US"),
      setCurrency: (currency) => set({ currency }),
      localeOverride: null,
      setLocaleOverride: (localeOverride) => set({ localeOverride }),
    }),
    {
      name: "talk2record-preferences",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
