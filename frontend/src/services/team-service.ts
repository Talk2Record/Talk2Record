import { api } from "@/lib/api";
import type {
  AdminUserRow,
  CreateInvitationResponse,
  InvitationRow,
  MembershipRow,
  OrgRole,
  SessionRow,
} from "@/types/platform";

export const teamService = {
  async listMembers() {
    const response = await api.get<MembershipRow[]>("/memberships/");
    return response.data;
  },

  async listInvitations(status?: InvitationRow["status"]) {
    const response = await api.get<InvitationRow[]>("/memberships/invitations/", {
      params: status ? { status } : undefined,
    });
    return response.data;
  },

  async invite(payload: { email: string; role: OrgRole }) {
    const response = await api.post<CreateInvitationResponse>("/memberships/invitations/", payload);
    return response.data;
  },

  async revokeInvitation(invitationId: number) {
    await api.post(`/memberships/invitations/${invitationId}/revoke/`);
  },

  async changeRole(membershipId: number, role: OrgRole) {
    const response = await api.patch<MembershipRow>(`/memberships/${membershipId}/role/`, { role });
    return response.data;
  },

  async removeMember(membershipId: number) {
    await api.delete(`/memberships/${membershipId}/`);
  },

  async lookupInvitation(token: string) {
    const response = await api.get<{
      organization: {
        id: number;
        name: string;
        slug: string;
        region?: string;
        timezone?: string;
        default_currency?: string;
        status?: string;
      };
      email: string;
      role: OrgRole;
      status: InvitationRow["status"];
      expiresAt: string;
    }>(`/invitations/${encodeURIComponent(token)}/`);
    return response.data;
  },

  async acceptInvitation(token: string) {
    const response = await api.post<MembershipRow>("/invitations/accept/", { token });
    return response.data;
  },
};

export const sessionService = {
  async list() {
    const response = await api.get<SessionRow[]>("/auth/sessions/");
    return response.data;
  },

  async revoke(sessionId: number) {
    await api.delete(`/auth/sessions/${sessionId}/`);
  },
};

export const adminUsersService = {
  async list(filters: { search?: string; status?: "active" | "suspended" | "inactive" } = {}) {
    const response = await api.get<AdminUserRow[] | { results: AdminUserRow[]; count?: number }>(
      "/admin/users/",
      {
        params: {
          ...(filters.search ? { search: filters.search } : {}),
          ...(filters.status ? { status: filters.status } : {}),
        },
      }
    );
    const data = response.data;
    return Array.isArray(data) ? data : data.results;
  },

  async retrieve(id: number) {
    const response = await api.get<AdminUserRow>(`/admin/users/${id}/`);
    return response.data;
  },

  async suspend(id: number, reason: string) {
    const response = await api.post<AdminUserRow>(`/admin/users/${id}/suspend/`, { reason });
    return response.data;
  },

  async reactivate(id: number) {
    const response = await api.post<AdminUserRow>(`/admin/users/${id}/reactivate/`);
    return response.data;
  },

  async impersonate(id: number) {
    const response = await api.post<{
      access: string;
      user: AdminUserRow;
      expiresInSeconds: number;
    }>(`/admin/users/${id}/impersonate/`);
    return response.data;
  },
};
