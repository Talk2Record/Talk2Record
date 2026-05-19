"use client";

import { Building2, Check, ChevronDown } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { Skeleton } from "@/shared/ui/skeleton";
import { useActiveOrg, useOrganizations } from "@/shared/hooks/use-organizations";

/**
 * Sidebar header element that lets the user see the active organization and,
 * when they belong to more than one, switch between them. The selection is
 * persisted via `useOrgStore` and broadcast through axios as `X-Org-Id`.
 *
 * Because the backend currently resolves the tenant from the JWT, a switch
 * mainly invalidates org-scoped caches and surfaces the desired tenant id to
 * the API. When the backend exposes a header-driven switch later, no UI
 * change is needed.
 */
export function OrgSwitcher() {
  const organizationsQuery = useOrganizations();
  const { active, organizations, switchTo } = useActiveOrg();

  if (organizationsQuery.isLoading) {
    return (
      <div className="bg-sidebar-accent/40 rounded-2xl px-3 py-2">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="mt-2 h-4 w-2/3" />
      </div>
    );
  }

  if (organizations.length === 0) {
    return (
      <div className="bg-sidebar-accent/40 rounded-2xl px-3 py-2 text-xs">
        <p className="text-sidebar-foreground/70">No organization</p>
        <p className="text-sidebar-foreground/60">Complete onboarding to create one.</p>
      </div>
    );
  }

  const label = active?.name ?? organizations[0]?.name ?? "Workspace";
  const region = active?.region ?? organizations[0]?.region ?? null;
  const onlyOne = organizations.length === 1;

  if (onlyOne) {
    return (
      <div
        aria-label="Active organization"
        className="bg-sidebar-accent/40 flex items-center gap-2 rounded-2xl px-3 py-2 text-left"
      >
        <Building2 className="text-sidebar-foreground/80 h-4 w-4 shrink-0" />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{label}</p>
          {region ? (
            <p className="text-sidebar-foreground/60 truncate text-[11px]">{region}</p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Switch organization"
        className="bg-sidebar-accent/40 hover:bg-sidebar-accent/60 flex w-full items-center gap-2 rounded-2xl px-3 py-2 text-left transition-colors"
      >
        <Building2 className="text-sidebar-foreground/80 h-4 w-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{label}</p>
          {region ? (
            <p className="text-sidebar-foreground/60 truncate text-[11px]">{region}</p>
          ) : null}
        </div>
        <ChevronDown className="text-sidebar-foreground/70 h-4 w-4 shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel>Switch workspace</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {organizations.map((org) => {
          const isActive = active?.id === org.id;
          return (
            <DropdownMenuItem
              key={org.id}
              onSelect={() => switchTo(org)}
              className="flex items-start gap-2"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{org.name}</p>
                <p className="text-muted-foreground truncate text-xs">
                  {[org.region, org.default_currency, org.status].filter(Boolean).join(" · ") ||
                    "—"}
                </p>
              </div>
              {isActive ? <Check className="text-primary mt-1 h-4 w-4 shrink-0" /> : null}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
