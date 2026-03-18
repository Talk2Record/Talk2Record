import { api } from "@/lib/api";

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  link_url: string;
  read_at: string | null;
  created_at: string;
}

export const notificationService = {
  async list(params?: { unread_only?: boolean }) {
    const response = await api.get<Notification[]>("/notifications/", {
      params: params?.unread_only !== undefined ? { unread_only: params.unread_only } : undefined,
    });
    return response.data;
  },

  async markRead(id: number) {
    const response = await api.post<Notification>(`/notifications/${id}/mark_read/`);
    return response.data;
  },

  async markAllRead() {
    const response = await api.post<{ marked_count: number }>("/notifications/mark_all_read/");
    return response.data;
  },
};
