import type { SupportedCurrency } from "@/types/platform";

export const supportedCurrencies: SupportedCurrency[] = ["USD", "EUR", "GBP", "KES", "INR"];

const localeCurrencyMap: Record<string, SupportedCurrency> = {
  en_GB: "GBP",
  en_KE: "KES",
  en_IN: "INR",
  es_ES: "EUR",
  fr_FR: "EUR",
};

export function resolveDefaultCurrency(locale: string): SupportedCurrency {
  return localeCurrencyMap[locale] || "USD";
}

export function formatCurrency(
  value: number,
  currency: SupportedCurrency,
  locale = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "KES" ? 0 : 2,
  }).format(value);
}

export function formatCompactNumber(value: number, locale = "en-US"): string {
  return new Intl.NumberFormat(locale, {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatDate(value: string, locale = "en-US"): string {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
