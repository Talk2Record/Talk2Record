"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CreditCard,
  LayoutDashboard,
  Link2,
  LogOut,
  Menu,
  ScrollText,
  Settings,
} from "lucide-react";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useTranslations } from "@/shared/lib/i18n/use-translations";
import { Logo } from "@/shared/components/logo";
import { CurrencySwitcher } from "@/shared/components/currency-switcher";
import { ThemeToggle } from "@/shared/components/theme-toggle";
import LanguageSwitcher from "@/shared/components/language-switcher";
import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";
import { Sheet, SheetContent, SheetTrigger } from "@/shared/ui/sheet";

type MenuItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
};

interface SidebarContentProps {
  pathname: string;
  menuItems: MenuItem[];
  logout: () => void;
  onNavigate?: () => void;
  workspaceLabel: string;
  userEmail?: string;
  logoutLabel: string;
}

const SidebarContent = ({
  pathname,
  menuItems,
  logout,
  onNavigate,
  workspaceLabel,
  userEmail,
  logoutLabel,
}: SidebarContentProps) => (
  <div className="bg-background flex h-full flex-col">
    <div className="border-border flex h-16 items-center gap-3 border-b px-4">
      <Logo size={28} className="h-7 w-7" />
      <div>
        <p className="text-sm font-semibold">Talk2Record</p>
        <p className="text-muted-foreground text-xs">{workspaceLabel}</p>
      </div>
    </div>

    <div className="border-border border-b px-4 py-3">
      <p className="text-xs font-medium">{userEmail}</p>
      <p className="text-muted-foreground text-xs">Operations workspace</p>
    </div>

    <nav className="flex-1 space-y-1 px-3 py-4">
      {menuItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"
            )}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>

    <div className="border-border bg-muted/30 space-y-2 border-t p-3">
      <div className="grid grid-cols-3 gap-2">
        <ThemeToggle />
        <LanguageSwitcher />
        <CurrencySwitcher />
      </div>
      <Button variant="outline" className="w-full justify-start gap-2" onClick={logout}>
        <LogOut className="h-4 w-4" />
        {logoutLabel}
      </Button>
    </div>
  </div>
);

export const Sidebar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  const { locale } = useLanguage();
  const pathname = usePathname();
  const messages = getTranslations(locale);
  const { t } = useTranslations(messages);

  const menuItems: MenuItem[] = [
    { label: t("navigation.dashboard"), href: "/dashboard", icon: LayoutDashboard },
    { label: t("navigation.records"), href: "/dashboard/records", icon: ScrollText },
    { label: t("navigation.analytics"), href: "/dashboard/analytics", icon: BarChart3 },
    { label: t("navigation.integrations"), href: "/dashboard/integrations", icon: Link2 },
    { label: t("navigation.billing"), href: "/dashboard/billing", icon: CreditCard },
    { label: t("navigation.settings"), href: "/dashboard/settings", icon: Settings },
  ];

  return (
    <>
      <div className="bg-background border-border fixed top-0 right-0 left-0 z-40 flex h-14 items-center border-b px-4 md:hidden">
        <div className="flex flex-1 items-center justify-start gap-3">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="-ml-1 h-8 w-8">
                <Menu className="h-5 w-5" />
                <span className="sr-only">{t("sidebar.menu")}</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] p-0">
              <SidebarContent
                pathname={pathname}
                menuItems={menuItems}
                logout={logout}
                onNavigate={() => setMobileOpen(false)}
                workspaceLabel={t("sidebar.workspace")}
                userEmail={user?.email}
                logoutLabel={t("navigation.logout")}
              />
            </SheetContent>
          </Sheet>
          <h1 className="truncate text-lg font-semibold">Talk2Record</h1>
        </div>
      </div>

      <aside className="bg-background border-border hidden h-screen w-72 shrink-0 border-r md:flex">
        <SidebarContent
          pathname={pathname}
          menuItems={menuItems}
          logout={logout}
          workspaceLabel={t("sidebar.workspace")}
          userEmail={user?.email}
          logoutLabel={t("navigation.logout")}
        />
      </aside>
    </>
  );
};
