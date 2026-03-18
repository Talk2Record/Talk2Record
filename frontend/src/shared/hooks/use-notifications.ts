"use client";

import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth-store";
import { notificationService, type Notification } from "@/services/notification-service";
import { connectNotificationWebSocket } from "@/lib/websocket";
import { toast } from "@/shared/hooks/use-toast";

const NOTIFICATIONS_QUERY_KEY = ["notifications"] as const;

function getWsBaseUrl(): string {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return baseUrl.replace(/\/$/, "");
}

export function useNotifications() {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const isAuthenticated = !!accessToken;
  const cleanupRef = useRef<(() => void) | null>(null);

  const {
    data: notifications = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: [...NOTIFICATIONS_QUERY_KEY, !!accessToken],
    queryFn: () => notificationService.list(),
    enabled: isAuthenticated,
  });

  const unreadCount = notifications.filter((n) => !n.read_at).length;

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }
      return;
    }

    const baseUrl = getWsBaseUrl();
    cleanupRef.current = connectNotificationWebSocket(
      baseUrl,
      accessToken,
      (data) => {
        const notification = data as Notification;
        if (notification?.id && notification?.title) {
          queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
          toast({
            title: notification.title,
            description: notification.message || undefined,
          });
        }
      }
    );

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }
    };
  }, [isAuthenticated, accessToken, queryClient]);

  const markRead = async (id: number) => {
    await notificationService.markRead(id);
    queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
  };

  const markAllRead = async () => {
    await notificationService.markAllRead();
    queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_QUERY_KEY });
  };

  return {
    notifications,
    unreadCount,
    isLoading,
    markRead,
    markAllRead,
    refetch,
  };
}
