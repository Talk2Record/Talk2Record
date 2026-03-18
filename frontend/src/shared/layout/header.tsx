"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { Logo } from "@/shared/components/logo";
import { CurrencySwitcher } from "@/shared/components/currency-switcher";
import LanguageSwitcher from "@/shared/components/language-switcher";
import { ThemeToggle } from "@/shared/components/theme-toggle";
import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";

const Header = () => {
  const { locale } = useLanguage();
  const { user } = useAuth();
  const pathname = usePathname();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navItems = [
    { href: "/", label: t("navigation.home") },
    { href: "/features", label: t("navigation.features") },
    { href: "/pricing", label: t("navigation.pricing") },
    { href: "/docs", label: t("navigation.docs") },
  ];

  return (
    <header className="border-border/80 bg-background/88 supports-backdrop-filter:bg-background/70 sticky top-0 z-50 w-full border-b backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative flex h-16 items-center justify-between">
          <div className="z-10 flex items-center">
            <Link href="/" className="flex items-center gap-3" aria-label={t("common.appName")}>
              <div className="bg-brand-gradient rounded-2xl p-px shadow-sm">
                <div className="bg-background rounded-[15px] px-2 py-1.5">
                  <Logo size={28} className="h-7 w-auto" />
                </div>
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-semibold tracking-tight">{t("common.appName")}</p>
                <p className="text-muted-foreground text-xs">Voice to business intelligence</p>
              </div>
            </Link>
          </div>

          <nav className="absolute top-1/2 left-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center gap-1 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition-all",
                  pathname === item.href
                    ? "bg-primary/10 text-primary shadow-sm"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="z-10 hidden items-center gap-2 md:flex">
            <div className="border-border/80 mr-2 flex items-center gap-1 border-r pr-2">
              <ThemeToggle />
              <LanguageSwitcher />
              <CurrencySwitcher />
            </div>

            {user ? (
              <Link href="/dashboard">
                <Button size="sm" className="h-9 rounded-full px-4 text-xs">
                  {t("navigation.dashboard")}
                </Button>
              </Link>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login">
                  <Button variant="ghost" size="sm" className="h-9 rounded-full px-4 text-xs">
                    {t("navigation.login")}
                  </Button>
                </Link>
                <Link href="/register">
                  <Button size="sm" className="h-9 rounded-full px-4 text-xs shadow-md">
                    {t("navigation.register")}
                  </Button>
                </Link>
              </div>
            )}
          </div>

          <div className="z-10 flex items-center gap-2 md:hidden">
            <ThemeToggle />
            <LanguageSwitcher />
            <CurrencySwitcher />
            <Button
              variant="ghost"
              size="sm"
              className="h-9 w-9 rounded-full p-0"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="border-border/80 bg-background/96 border-t md:hidden">
          <div className="mx-auto max-w-7xl space-y-4 px-4 py-4">
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                    pathname === item.href
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="border-border/80 border-t pt-3">
              {user ? (
                <Link href="/dashboard" onClick={() => setMobileMenuOpen(false)}>
                  <Button size="sm" className="w-full rounded-xl">
                    {t("navigation.dashboard")}
                  </Button>
                </Link>
              ) : (
                <div className="grid gap-2">
                  <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                    <Button variant="outline" size="sm" className="w-full rounded-xl">
                      {t("navigation.login")}
                    </Button>
                  </Link>
                  <Link href="/register" onClick={() => setMobileMenuOpen(false)}>
                    <Button size="sm" className="w-full rounded-xl">
                      {t("navigation.register")}
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
