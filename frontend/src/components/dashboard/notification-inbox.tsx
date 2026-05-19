"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  Check,
  CheckCheck,
  CircleAlert,
  CreditCard,
  FileCheck,
  Mail,
  Plug,
} from "lucide-react";
import { useNotifications } from "@/shared/hooks/use-notifications";
import { formatRelativeTime } from "@/lib/format";
import { cn } from "@/shared/lib/utils";
import type { Notification } from "@/services/notification-service";

interface IconFor {
  (_type: string): React.ReactNode;
}

const iconFor: IconFor = (type) => {
  switch (type) {
    case "record_stored":
      return <FileCheck className="h-4 w-4 text-emerald-500" />;
    case "record_failed":
      return <CircleAlert className="text-destructive h-4 w-4" />;
    case "membership_invite":
      return <Mail className="h-4 w-4 text-sky-500" />;
    case "billing_subscription":
    case "billing_payment":
      return <CreditCard className="h-4 w-4 text-violet-500" />;
    case "integration_connected":
      return <Plug className="h-4 w-4 text-amber-500" />;
    default:
      return <Bell className="text-muted-foreground h-4 w-4" />;
  }
};

/**
 * Notification center bell + popover wired to:
 *   - `useNotifications` for REST + WS cache
 *   - the global router for deep links
 *
 * UX rules:
 *   - clicking a row navigates to `link_url` AND marks it read
 *   - "Mark all" wipes the unread state with a single mutation
 *   - escape / click outside closes the panel
 */
export function NotificationInbox() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  // While the inbox is open we silence the auto-toast on new pushes — the
  // panel itself already shows them.
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications({
    toastOnReceive: !isOpen,
  });

  useEffect(() => {
    if (!isOpen) return;

    const onClick = (event: MouseEvent) => {
      if (!wrapperRef.current) return;
      if (wrapperRef.current.contains(event.target as Node)) return;
      setIsOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [isOpen]);

  const grouped = groupByRecency(notifications);

  function handleSelect(notification: Notification) {
    if (!notification.read_at) {
      void markRead(notification.id);
    }
    if (notification.link_url) {
      const isExternal = /^https?:\/\//i.test(notification.link_url);
      if (isExternal) {
        window.open(notification.link_url, "_blank", "noopener,noreferrer");
      } else {
        router.push(notification.link_url);
      }
    }
    setIsOpen(false);
  }

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-label="Notifications"
        className="border-input bg-background hover:bg-muted relative inline-flex h-9 w-9 items-center justify-center rounded-full border text-sm transition-colors"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 ? (
          <span className="bg-destructive text-destructive-foreground absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-semibold">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div
          role="dialog"
          aria-label="Notifications"
          className="bg-popover text-popover-foreground border-border absolute top-12 right-0 z-50 w-[360px] origin-top-right rounded-xl border shadow-lg"
        >
          <div className="border-border flex items-center justify-between border-b px-4 py-3">
            <div>
              <p className="text-sm font-semibold">Notifications</p>
              <p className="text-muted-foreground text-xs">
                {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
              </p>
            </div>
            {unreadCount > 0 ? (
              <button
                type="button"
                onClick={() => void markAllRead()}
                className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-xs"
              >
                <CheckCheck className="h-3.5 w-3.5" /> Mark all
              </button>
            ) : null}
          </div>

          <div className="max-h-[60vh] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="text-muted-foreground px-4 py-8 text-center text-sm">
                You have no notifications.
              </div>
            ) : (
              <>
                {grouped.today.length > 0 ? (
                  <NotificationGroup
                    title="Today"
                    notifications={grouped.today}
                    onSelect={handleSelect}
                  />
                ) : null}
                {grouped.earlier.length > 0 ? (
                  <NotificationGroup
                    title="Earlier"
                    notifications={grouped.earlier}
                    onSelect={handleSelect}
                  />
                ) : null}
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

interface NotificationGroupProps {
  title: string;
  notifications: Notification[];
  onSelect: (_notification: Notification) => void;
}

function NotificationGroup({ title, notifications, onSelect }: NotificationGroupProps) {
  return (
    <div>
      <p className="bg-muted/40 text-muted-foreground sticky top-0 px-4 py-2 text-[11px] font-semibold tracking-wide uppercase">
        {title}
      </p>
      <ul className="divide-border divide-y">
        {notifications.map((n) => (
          <li key={n.id}>
            <button
              type="button"
              onClick={() => onSelect(n)}
              className={cn(
                "hover:bg-muted/40 flex w-full items-start gap-3 px-4 py-3 text-left text-sm transition-colors",
                !n.read_at && "bg-primary/5"
              )}
            >
              <span className="mt-0.5 shrink-0">{iconFor(n.type)}</span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className={cn("truncate font-medium", !n.read_at && "text-foreground")}>
                    {n.title}
                  </span>
                  <span className="text-muted-foreground shrink-0 text-[11px]">
                    {formatRelativeTime(n.created_at)}
                  </span>
                </span>
                {n.message ? (
                  <span className="text-muted-foreground line-clamp-2 block text-xs">
                    {n.message}
                  </span>
                ) : null}
              </span>
              {!n.read_at ? (
                <span className="bg-primary mt-1.5 h-2 w-2 shrink-0 rounded-full" />
              ) : (
                <Check className="text-muted-foreground/60 mt-1 h-3.5 w-3.5 shrink-0" />
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function groupByRecency(notifications: Notification[]) {
  const dayStart = new Date();
  dayStart.setHours(0, 0, 0, 0);
  const threshold = dayStart.getTime();
  const today: Notification[] = [];
  const earlier: Notification[] = [];
  for (const n of notifications) {
    const t = new Date(n.created_at).getTime();
    if (Number.isFinite(t) && t >= threshold) today.push(n);
    else earlier.push(n);
  }
  return { today, earlier };
}
