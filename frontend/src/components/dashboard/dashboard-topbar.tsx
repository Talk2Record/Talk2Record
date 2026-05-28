"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { ChevronDown, LogOut, Search, Settings } from "lucide-react";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { useAuth } from "@/shared/lib/auth/auth-context";
import LanguageSwitcher from "@/shared/components/language-switcher";
import { CurrencySwitcher } from "@/shared/components/currency-switcher";
import { ThemeToggle } from "@/shared/components/theme-toggle";
import { LiveIndicator } from "@/components/dashboard/live-indicator";
import { NotificationInbox } from "@/components/dashboard/notification-inbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { Button } from "@/shared/ui/button";

interface DashboardTopbarProps {
  onOpenPalette: () => void;
}

// SSR-safe platform sniff: returns "Ctrl K" on the server (and during the
// initial client render) so React doesn't see a hydration mismatch. After
// commit, `useSyncExternalStore` swaps in the real value on macOS clients.
const NEVER_CHANGES = () => () => {};
const getShortcutLabel = () =>
  typeof navigator !== "undefined" && /Mac|iPod|iPhone|iPad/.test(navigator.platform)
    ? "⌘ K"
    : "Ctrl K";
const getShortcutLabelServer = () => "Ctrl K";

export function DashboardTopbar({ onOpenPalette }: DashboardTopbarProps) {
  const { locale } = useLanguage();
  const { user, logout } = useAuth();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);
  const shortcutLabel = useSyncExternalStore(
    NEVER_CHANGES,
    getShortcutLabel,
    getShortcutLabelServer
  );

  return (
    <div className="border-border/80 bg-background/88 sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b px-4 backdrop-blur-xl md:px-8">
      <button
        type="button"
        onClick={onOpenPalette}
        aria-label={t("dashboard.topbar.searchPlaceholder")}
        className="border-primary/10 bg-background/90 text-muted-foreground hover:bg-muted hidden h-11 w-full max-w-md items-center gap-3 rounded-full border px-4 text-sm transition-colors md:flex"
      >
        <Search className="h-4 w-4 shrink-0" />
        <span className="flex-1 truncate text-left">{t("dashboard.topbar.searchPlaceholder")}</span>
        <kbd className="border-border bg-muted text-muted-foreground inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium">
          {shortcutLabel}
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-2">
        <LiveIndicator />
        <ThemeToggle />
        <LanguageSwitcher />
        <CurrencySwitcher />
        <NotificationInbox />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="outline"
              className="brand-panel border-primary/10 h-auto max-w-[220px] rounded-2xl border px-3 py-2 text-left"
            >
              <span className="flex min-w-0 items-center gap-2">
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {user?.name || "Workspace user"}
                  </span>
                  <span className="text-muted-foreground block truncate text-xs">
                    {user?.email}
                  </span>
                </span>
                <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0" />
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <p className="truncate text-sm font-medium">{user?.name || "Workspace user"}</p>
              <p className="text-muted-foreground truncate text-xs">{user?.email}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings">
                <Settings className="h-4 w-4" />
                {t("navigation.settings")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => {
                void logout();
              }}
            >
              <LogOut className="h-4 w-4" />
              {t("navigation.logout")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
