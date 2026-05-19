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

/**
 * Lightweight relative-time string ("2 minutes ago", "just now") for
 * notification rows. We avoid `date-fns` to keep the bundle slim — the
 * native `Intl.RelativeTimeFormat` covers what we need.
 */
export function formatRelativeTime(value: string, locale = "en-US"): string {
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  const target = new Date(value).getTime();
  if (Number.isNaN(target)) return "";
  const diffSeconds = Math.round((target - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);

  if (absSeconds < 60) return formatter.format(diffSeconds, "second");
  const minutes = Math.round(diffSeconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(diffSeconds / 3_600);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  const days = Math.round(diffSeconds / 86_400);
  if (Math.abs(days) < 7) return formatter.format(days, "day");
  const weeks = Math.round(diffSeconds / 604_800);
  if (Math.abs(weeks) < 5) return formatter.format(weeks, "week");
  const months = Math.round(diffSeconds / 2_592_000);
  if (Math.abs(months) < 12) return formatter.format(months, "month");
  const years = Math.round(diffSeconds / 31_536_000);
  return formatter.format(years, "year");
}
