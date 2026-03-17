export type { Locale } from "@/shared/lib/config/site";
export {
  supportedLocales as LOCALES,
  defaultLocale as DEFAULT_LOCALE,
} from "@/shared/lib/config/site";

export interface Translations {
  [key: string]: string | Translations;
}

export interface I18nConfig {
  locales: readonly string[];
  defaultLocale: string;
  localeDetection: boolean;
}

import { supportedLocales, defaultLocale } from "@/shared/lib/config/site";

export const i18nConfig: I18nConfig = {
  locales: supportedLocales,
  defaultLocale,
  localeDetection: true,
};

export type TranslationKeys = string;
