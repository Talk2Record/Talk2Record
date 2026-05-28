"use client";

import type React from "react";

import type { Locale } from "@/shared/lib/i18n/types";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { DEFAULT_LOCALE } from "@/shared/lib/i18n/types";

interface LanguageContextType {
  locale: Locale;
  setLocale: (_locale: Locale) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

function readStoredLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  const stored = window.localStorage.getItem("locale") as Locale | null;
  return stored ?? DEFAULT_LOCALE;
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readStoredLocale);

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem("locale", newLocale);
  };

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = "ltr";
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale }), [locale]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return context;
}
