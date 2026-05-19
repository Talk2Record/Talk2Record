"use client";

import {
  Activity,
  BarChart3,
  Cpu,
  CreditCard,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  Monitor,
  Plug,
  ScrollText,
  Settings,
  ShieldAlert,
  UsersRound,
} from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/shared/ui/sheet";

import { Button } from "@/shared/ui/button";
import { CurrencySwitcher } from "@/shared/components/currency-switcher";
import LanguageSwitcher from "@/shared/components/language-switcher";
import Link from "next/link";
import { Logo } from "@/shared/components/logo";
import { OrgSwitcher } from "@/components/dashboard/org-switcher";
import { ThemeToggle } from "@/shared/components/theme-toggle";
import { cn } from "@/shared/lib/utils";
import { getTranslations } from "@/shared/lib/i18n/get-translations";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useLanguage } from "@/shared/lib/i18n/language-context";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "@/shared/lib/i18n/use-translations";

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
  <div className="bg-sidebar text-sidebar-foreground flex h-full flex-col overflow-hidden">
    <div className="border-sidebar-border flex min-h-24 flex-col justify-center gap-3 border-b px-5 py-5">
      <div className="flex items-center gap-3">
        <div className="bg-brand-gradient rounded-2xl p-px shadow-sm">
          <div className="bg-sidebar rounded-[15px] px-2 py-1.5">
            <Logo size={28} className="h-7 w-auto" />
          </div>
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight">Talk2Record</p>
          <p className="text-sidebar-foreground/70 text-xs">{workspaceLabel}</p>
        </div>
      </div>
      <div className="bg-sidebar-accent text-sidebar-accent-foreground inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
        Structured business intelligence
      </div>
    </div>

    <div className="border-sidebar-border space-y-3 border-b px-5 py-4">
      <OrgSwitcher />
      <div>
        <p className="text-xs font-medium">{userEmail}</p>
        <p className="text-sidebar-foreground/65 text-xs">Operations workspace</p>
      </div>
    </div>

    <nav className="flex-1 space-y-1.5 px-4 py-5">
      {menuItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm font-medium transition-all",
              isActive
                ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-md"
                : "text-sidebar-foreground/72 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>

    <div className="border-sidebar-border bg-sidebar/95 space-y-3 border-t p-4">
      <div className="grid grid-cols-3 gap-2">
        <ThemeToggle />
        <LanguageSwitcher />
        <CurrencySwitcher />
      </div>
      <Button variant="outline" className="w-full justify-start gap-2 rounded-xl" onClick={logout}>
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

  const isAdminRole = user?.role === "owner" || user?.role === "admin";
  const isPlatformStaff = Boolean(user?.isStaff || user?.isSuperuser);

  const menuItems: MenuItem[] = [
    { label: t("navigation.dashboard"), href: "/dashboard", icon: LayoutDashboard },
    { label: t("navigation.records"), href: "/dashboard/records", icon: ScrollText },
    { label: t("navigation.analytics"), href: "/dashboard/analytics", icon: BarChart3 },
    { label: "Usage", href: "/dashboard/usage", icon: Activity },
    { label: t("navigation.billing"), href: "/dashboard/billing", icon: CreditCard },
    { label: "Integrations", href: "/dashboard/integrations", icon: Plug },
    ...(isAdminRole ? [{ label: "Team", href: "/dashboard/team", icon: UsersRound }] : []),
    { label: t("navigation.settings"), href: "/dashboard/settings", icon: Settings },
    { label: t("navigation.apiKeys"), href: "/dashboard/settings/api-keys", icon: KeyRound },
    ...(isAdminRole ? [{ label: "AI", href: "/dashboard/settings/ai", icon: Cpu }] : []),
    { label: "Sessions", href: "/dashboard/settings/sessions", icon: Monitor },
    ...(isPlatformStaff
      ? [{ label: "Platform admin", href: "/dashboard/admin/users", icon: ShieldAlert }]
      : []),
  ];

  return (
    <>
      <div className="bg-background/92 border-border/80 fixed top-0 right-0 left-0 z-40 flex h-14 items-center border-b px-4 backdrop-blur-xl md:hidden">
        <div className="flex flex-1 items-center justify-start gap-3">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="-ml-1 h-8 w-8 rounded-full">
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
          <div>
            <h1 className="truncate text-lg font-semibold">Talk2Record</h1>
            <p className="text-muted-foreground text-xs">Business intelligence from voice</p>
          </div>
        </div>
      </div>

      <aside className="border-sidebar-border sticky top-0 hidden h-screen shrink-0 border-r md:flex">
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
