import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { resolveDefaultCurrency } from "@/lib/format";
import type { BillingInterval, SupportedCurrency } from "@/types/platform";
import type { Locale } from "@/shared/lib/i18n/types";

interface PreferencesState {
  currency: SupportedCurrency;
  setCurrency: (_currency: SupportedCurrency) => void;
  localeOverride: Locale | null;
  setLocaleOverride: (_locale: Locale) => void;
  /**
   * User's preferred billing interval. Persisted across sessions so the
   * plan-catalog grid + checkout modal remember the toggle setting.
   * Default is "month" — most users start on monthly and opt into annual.
   */
  billingInterval: BillingInterval;
  setBillingInterval: (_interval: BillingInterval) => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      currency: resolveDefaultCurrency("en_US"),
      setCurrency: (currency) => set({ currency }),
      localeOverride: null,
      setLocaleOverride: (localeOverride) => set({ localeOverride }),
      billingInterval: "month",
      setBillingInterval: (billingInterval) => set({ billingInterval }),
    }),
    {
      name: "talk2record-preferences",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
