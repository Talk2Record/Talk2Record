"use client";

import { useCallback, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth-store";
import { notificationService, type Notification } from "@/services/notification-service";
import { wsBus } from "@/lib/ws-bus";
import { toast } from "@/shared/hooks/use-toast";
import { useWsBusLifecycle } from "@/shared/hooks/use-ws-bus";

export const NOTIFICATIONS_QUERY_KEY = ["notifications"] as const;

interface UseNotificationsOptions {
  /**
   * Show a toast for every incoming WebSocket notification. Defaults to
   * true on the global hook (DashboardShell). The `<NotificationInbox />`
   * sets this to false to avoid double-toasting when the panel is open.
   */
  toastOnReceive?: boolean;
}

/**
 * Single source of truth for the notification REST cache + WS push.
 *
 * Mount once at the shell level so the WS lifecycle is managed in one place
 * but every component (topbar bell, deep-link router, banners) can read the
 * same React Query cache.
 */
export function useNotifications(options: UseNotificationsOptions = {}) {
  const { toastOnReceive = true } = options;
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const isAuthenticated = Boolean(accessToken);

  useWsBusLifecycle();

  const query = useQuery({
    queryKey: NOTIFICATIONS_QUERY_KEY,
    queryFn: () => notificationService.list(),
    enabled: isAuthenticated,
  });

  /** Subscribe to incoming WS notifications and reconcile the cache. */
  useEffect(() => {
    if (!isAuthenticated) return;

    return wsBus.on("notification", (incoming) => {
      queryClient.setQueryData<Notification[]>(NOTIFICATIONS_QUERY_KEY, (prev) => {
        if (!prev) return [incoming as Notification];
        // Replace existing or prepend new.
        const idx = prev.findIndex((n) => n.id === incoming.id);
        if (idx >= 0) {
          const next = prev.slice();
          next[idx] = incoming as Notification;
          return next;
        }
        return [incoming as Notification, ...prev];
      });

      if (toastOnReceive && incoming.title) {
        toast({
          title: incoming.title,
          description: incoming.message || undefined,
        });
      }
    });
  }, [isAuthenticated, queryClient, toastOnReceive]);

  const markReadMutation = useMutation({
    mutationFn: notificationService.markRead,
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
      const previous = queryClient.getQueryData<Notification[]>(NOTIFICATIONS_QUERY_KEY);
      queryClient.setQueryData<Notification[]>(NOTIFICATIONS_QUERY_KEY, (prev) =>
        prev?.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
      return { previous };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, ctx.previous);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: notificationService.markAllRead,
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
      const previous = queryClient.getQueryData<Notification[]>(NOTIFICATIONS_QUERY_KEY);
      const now = new Date().toISOString();
      queryClient.setQueryData<Notification[]>(NOTIFICATIONS_QUERY_KEY, (prev) =>
        prev?.map((n) => (n.read_at ? n : { ...n, read_at: now }))
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(NOTIFICATIONS_QUERY_KEY, ctx.previous);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
    },
  });

  const markRead = useCallback(
    (id: number) => markReadMutation.mutateAsync(id),
    [markReadMutation]
  );

  const markAllRead = useCallback(() => markAllReadMutation.mutateAsync(), [markAllReadMutation]);

  const notifications = query.data ?? [];
  const unreadCount = notifications.filter((n) => !n.read_at).length;

  return {
    notifications,
    unreadCount,
    isLoading: query.isLoading,
    refetch: query.refetch,
    markRead,
    markAllRead,
  };
}
