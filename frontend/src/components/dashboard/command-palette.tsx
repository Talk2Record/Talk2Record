"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  BarChart3,
  Command,
  CreditCard,
  Cpu,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Plug,
  ScrollText,
  Search,
  Settings,
  ShieldAlert,
  Sparkles,
  UsersRound,
} from "lucide-react";

import { Dialog, DialogContent, DialogTitle } from "@/shared/ui/dialog";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { useRecords } from "@/shared/hooks/use-records";
import { useRole } from "@/shared/hooks/use-role";
import { cn } from "@/shared/lib/utils";
import type { LucideIcon } from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (_open: boolean) => void;
}

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  hint?: string;
  icon: LucideIcon;
  keywords?: string;
  onSelect: () => void;
}

interface CommandGroup {
  id: string;
  heading: string;
  items: CommandItem[];
}

/**
 * Command palette wired against existing app routes plus a live records
 * search backed by the records query cache. We intentionally do not
 * implement any "actions" that mutate data here: the palette is a
 * navigation surface only, which matches users' expectations and keeps the
 * keyboard surface predictable.
 */
export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const { logout } = useAuth();
  const { atLeast, isStaff } = useRole();
  const { data: records = [] } = useRecords();

  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const isAdmin = atLeast("admin");
  const isPlatformStaff = isStaff;

  const navigate = useCallback(
    (href: string) => {
      onOpenChange(false);
      router.push(href);
    },
    [onOpenChange, router]
  );

  const baseGroups = useMemo<CommandGroup[]>(() => {
    const groups: CommandGroup[] = [
      {
        id: "go",
        heading: "Go to",
        items: [
          {
            id: "go:dashboard",
            label: "Dashboard overview",
            icon: LayoutDashboard,
            keywords: "home start",
            onSelect: () => navigate("/dashboard"),
          },
          {
            id: "go:records",
            label: "Records",
            icon: ScrollText,
            keywords: "voice notes transactions",
            onSelect: () => navigate("/dashboard/records"),
          },
          {
            id: "go:analytics",
            label: "Analytics",
            icon: BarChart3,
            keywords: "stats charts",
            onSelect: () => navigate("/dashboard/analytics"),
          },
          {
            id: "go:usage",
            label: "Usage",
            icon: Activity,
            keywords: "quota limits",
            onSelect: () => navigate("/dashboard/usage"),
          },
          {
            id: "go:billing",
            label: "Billing",
            icon: CreditCard,
            keywords: "subscription plan invoices",
            onSelect: () => navigate("/dashboard/billing"),
          },
          {
            id: "go:integrations",
            label: "Integrations",
            icon: Plug,
            keywords: "whatsapp connections",
            onSelect: () => navigate("/dashboard/integrations"),
          },
        ],
      },
      {
        id: "settings",
        heading: "Settings",
        items: [
          {
            id: "settings:overview",
            label: "Account settings",
            icon: Settings,
            keywords: "profile preferences",
            onSelect: () => navigate("/dashboard/settings"),
          },
          {
            id: "settings:api-keys",
            label: "API keys",
            icon: KeyRound,
            keywords: "tokens credentials",
            onSelect: () => navigate("/dashboard/settings/api-keys"),
          },
          {
            id: "settings:sessions",
            label: "Active sessions",
            icon: Sparkles,
            keywords: "devices logins",
            onSelect: () => navigate("/dashboard/settings/sessions"),
          },
        ],
      },
    ];

    if (isAdmin) {
      groups.push({
        id: "team",
        heading: "Team",
        items: [
          {
            id: "team:overview",
            label: "Team members",
            icon: UsersRound,
            keywords: "invites roles",
            onSelect: () => navigate("/dashboard/team"),
          },
          {
            id: "team:ai",
            label: "AI settings",
            icon: Cpu,
            keywords: "model prompt",
            onSelect: () => navigate("/dashboard/settings/ai"),
          },
        ],
      });
    }

    if (isPlatformStaff) {
      groups.push({
        id: "platform",
        heading: "Platform admin",
        items: [
          {
            id: "platform:users",
            label: "Platform users",
            icon: ShieldAlert,
            keywords: "impersonate accounts",
            onSelect: () => navigate("/dashboard/admin/users"),
          },
        ],
      });
    }

    groups.push({
      id: "session",
      heading: "Session",
      items: [
        {
          id: "session:logout",
          label: "Sign out",
          icon: LogOut,
          keywords: "logout exit",
          onSelect: () => {
            onOpenChange(false);
            void logout();
          },
        },
      ],
    });

    return groups;
  }, [isAdmin, isPlatformStaff, logout, navigate, onOpenChange]);

  const recordsGroup = useMemo<CommandGroup | null>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return null;
    const matches = records
      .filter((record) => {
        const haystack = `${record.customer} ${record.product} ${record.id}`.toLowerCase();
        return haystack.includes(q);
      })
      .slice(0, 6)
      .map<CommandItem>((record) => ({
        id: `record:${record.id}`,
        label: `${record.customer} — ${record.product}`,
        description: `Record · ${record.status}`,
        hint: record.id,
        icon: FileText,
        keywords: `${record.customer} ${record.product} ${record.id} ${record.status}`,
        onSelect: () => navigate(`/dashboard/records/${record.id}`),
      }));

    if (matches.length === 0) return null;
    return { id: "records-search", heading: "Records", items: matches };
  }, [navigate, query, records]);

  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const groups: CommandGroup[] = recordsGroup ? [recordsGroup, ...baseGroups] : baseGroups;
    if (!q) return groups;
    return groups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => matches(item, q)),
      }))
      .filter((group) => group.items.length > 0);
  }, [baseGroups, query, recordsGroup]);

  const flatItems = useMemo(() => filteredGroups.flatMap((group) => group.items), [filteredGroups]);

  // Reset the highlighted item whenever the search or open state changes.
  // We use the "track previous value during render" pattern instead of a
  // setState-in-effect so the React Compiler doesn't flag cascading renders.
  const [prevResetKey, setPrevResetKey] = useState<string>(`${open}|${query}`);
  const resetKey = `${open}|${query}`;
  if (prevResetKey !== resetKey) {
    setPrevResetKey(resetKey);
    setActiveIndex(0);
  }

  const runItem = useCallback(
    (index: number) => {
      const item = flatItems[index];
      if (!item) return;
      item.onSelect();
    },
    [flatItems]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((prev) => (flatItems.length === 0 ? 0 : (prev + 1) % flatItems.length));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((prev) =>
          flatItems.length === 0 ? 0 : (prev - 1 + flatItems.length) % flatItems.length
        );
      } else if (event.key === "Enter") {
        event.preventDefault();
        runItem(activeIndex);
      }
    },
    [activeIndex, flatItems.length, runItem]
  );

  // Clear the search input when the palette closes (track-previous pattern).
  const [prevOpen, setPrevOpen] = useState(open);
  if (prevOpen !== open) {
    setPrevOpen(open);
    if (!open) {
      setQuery("");
    }
  }

  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLButtonElement>(
      `[data-command-index='${activeIndex}']`
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0 sm:max-w-[640px]" onKeyDown={handleKeyDown}>
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <div className="border-border/60 flex items-center gap-2 border-b px-4 py-3">
          <Search className="text-muted-foreground h-4 w-4" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search records, pages, settings…"
            className="placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none"
          />
          <kbd className="border-border bg-muted text-muted-foreground hidden rounded border px-1.5 py-0.5 text-[10px] font-medium sm:inline-flex">
            Esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[60vh] overflow-y-auto py-2">
          {flatItems.length === 0 ? (
            <div className="text-muted-foreground px-4 py-8 text-center text-sm">
              <p>No matches.</p>
              <p className="mt-1 text-xs">Try a customer, product, or page name.</p>
            </div>
          ) : (
            <PaletteGroups
              groups={filteredGroups}
              activeIndex={activeIndex}
              onHover={setActiveIndex}
              onSelect={runItem}
            />
          )}
        </div>

        <div className="border-border/60 bg-muted/40 text-muted-foreground flex items-center justify-between gap-3 border-t px-4 py-2 text-[11px]">
          <span className="inline-flex items-center gap-1.5">
            <Command className="h-3 w-3" />
            Palette
          </span>
          <span className="hidden sm:inline">
            <kbd className="border-border bg-background mr-1 rounded border px-1 py-0.5">↑</kbd>
            <kbd className="border-border bg-background mr-1 rounded border px-1 py-0.5">↓</kbd>
            to navigate
            <kbd className="border-border bg-background mx-1 rounded border px-1 py-0.5">↵</kbd>
            to open
          </span>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface PaletteGroupsProps {
  groups: CommandGroup[];
  activeIndex: number;
  onHover: (_index: number) => void;
  onSelect: (_index: number) => void;
}

function PaletteGroups({ groups, activeIndex, onHover, onSelect }: PaletteGroupsProps) {
  let cursor = 0;
  return (
    <div className="space-y-1 px-2">
      {groups.map((group) => (
        <div key={group.id} className="pt-2">
          <p className="text-muted-foreground px-2 pb-1 text-[11px] font-medium tracking-wide uppercase">
            {group.heading}
          </p>
          <div className="space-y-0.5">
            {group.items.map((item) => {
              const index = cursor++;
              const Icon = item.icon;
              const isActive = index === activeIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  data-command-index={index}
                  onMouseEnter={() => onHover(index)}
                  onClick={() => onSelect(index)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                    isActive ? "bg-primary/10 text-foreground" : "hover:bg-muted/60"
                  )}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4 shrink-0",
                      isActive ? "text-primary" : "text-muted-foreground"
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm">{item.label}</p>
                    {item.description ? (
                      <p className="text-muted-foreground truncate text-xs">{item.description}</p>
                    ) : null}
                  </div>
                  {item.hint ? (
                    <span className="text-muted-foreground hidden font-mono text-[10px] sm:inline">
                      {item.hint.slice(0, 8)}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function matches(item: CommandItem, query: string): boolean {
  if (!query) return true;
  const haystack = `${item.label} ${item.description ?? ""} ${item.keywords ?? ""}`.toLowerCase();
  return haystack.includes(query);
}
