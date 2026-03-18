"use client";

import { Bell, Search } from "lucide-react";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { useAuth } from "@/shared/lib/auth/auth-context";
import LanguageSwitcher from "@/shared/components/language-switcher";
import { CurrencySwitcher } from "@/shared/components/currency-switcher";
import { ThemeToggle } from "@/shared/components/theme-toggle";
import { Input } from "@/shared/ui/input";
import { Button } from "@/shared/ui/button";

export function DashboardTopbar() {
  const { locale } = useLanguage();
  const { user } = useAuth();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);

  return (
    <div className="border-border/80 bg-background/88 sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b px-4 backdrop-blur-xl md:px-8">
      <div className="relative hidden w-full max-w-md md:block">
        <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
        <Input className="h-11 rounded-full border-primary/10 bg-background/90 pl-9" placeholder={t("dashboard.topbar.searchPlaceholder")} />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <LanguageSwitcher />
        <CurrencySwitcher />
        <Button variant="outline" size="icon" className="rounded-full">
          <Bell className="h-4 w-4" />
          <span className="sr-only">{t("dashboard.topbar.notifications")}</span>
        </Button>
        <div className="brand-panel hidden rounded-2xl border border-primary/10 px-3 py-2 text-right md:block">
          <p className="text-sm font-medium">{user?.name || "Workspace user"}</p>
          <p className="text-muted-foreground text-xs">{user?.email}</p>
        </div>
      </div>
    </div>
  );
}
