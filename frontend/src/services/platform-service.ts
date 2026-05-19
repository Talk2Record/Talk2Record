import { api } from "@/lib/api";
import type {
  AnalyticsSnapshot,
  AuthUser,
  BillingSnapshot,
  CreateOrganizationApiKeyInput,
  CreateOrganizationApiKeyResponse,
  DashboardOverview,
  LegalAcceptanceStatus,
  OnboardingStep,
  OrganizationApiKeyAuditEvent,
  OrganizationApiKeyRow,
  OrganizationSummary,
  SettingsProfile,
  SubscriptionRow,
} from "@/types/platform";
import {
  mapAnalyticsSnapshot,
  mapAuthUser,
  mapBillingSnapshot,
  mapDashboardOverview,
  mapOnboardingSteps,
  mapRecord,
  mapSettingsProfile,
} from "@/services/platform-mappers";

interface AuthSession {
  user: AuthUser;
  accessToken: string;
  refreshToken: string;
}

export const authService = {
  async login(email: string, password: string) {
    const response = await api.post<{
      user: Parameters<typeof mapAuthUser>[0];
      access: string;
      refresh: string;
    }>("/auth/login/", { email, password });

    return {
      user: mapAuthUser(response.data.user),
      accessToken: response.data.access,
      refreshToken: response.data.refresh,
    } satisfies AuthSession;
  },

  async register(payload: {
    name: string;
    company: string;
    email: string;
    password: string;
    acceptedDocumentKeys: string[];
  }) {
    await api.post("/auth/register/", payload);
    return authService.login(payload.email, payload.password);
  },

  async forgotPassword(email: string) {
    const response = await api.post<{ status: string }>("/auth/forgot-password/", { email });
    return response.data;
  },

  async completeOnboarding(payload: {
    voiceDataConsent: boolean;
    aiReviewAcknowledged: boolean;
    recordVerificationAcknowledged: boolean;
  }) {
    const response = await api.post<{ user: Parameters<typeof mapAuthUser>[0] }>(
      "/onboarding/complete/",
      payload
    );
    return mapAuthUser(response.data.user);
  },

  async getCurrentUser() {
    const response = await api.get<Parameters<typeof mapAuthUser>[0]>("/auth/me/");
    return mapAuthUser(response.data);
  },

  async logout(refreshToken: string) {
    await api.post("/auth/logout/", { refresh: refreshToken });
  },
};

export const dashboardService = {
  async getOverview() {
    const response = await api.get<DashboardOverview>("/dashboard/");
    return mapDashboardOverview(response.data);
  },
};

export const recordsService = {
  async list() {
    const response = await api.get<Array<Parameters<typeof mapRecord>[0]>>("/records/");
    return response.data.map(mapRecord);
  },

  async get(id: string) {
    const response = await api.get<Parameters<typeof mapRecord>[0]>(`/records/${id}/`);
    return mapRecord(response.data);
  },
};

export const analyticsService = {
  async getSnapshot() {
    const response = await api.get<AnalyticsSnapshot>("/analytics/");
    return mapAnalyticsSnapshot(response.data);
  },
};

export interface EntitlementRow {
  feature_key: string;
  enabled: boolean;
  limit: number;
  period: "none" | "monthly" | "yearly";
}

export const billingService = {
  async getSnapshot() {
    const response = await api.get<BillingSnapshot>("/billing/");
    return mapBillingSnapshot(response.data);
  },

  async listEntitlements() {
    const response = await api.get<EntitlementRow[]>("/billing/entitlements/");
    return response.data;
  },

  async checkout(payload: { plan: string; acceptedBillingTerms: boolean; provider?: string }) {
    const response = await api.post<{ status: string; checkoutUrl: string }>(
      "/billing/checkout/",
      payload
    );
    return response.data;
  },

  async listSubscriptions() {
    const response = await api.get<SubscriptionRow[]>("/subscriptions/");
    return response.data;
  },
};

export const onboardingService = {
  async getSteps() {
    const response = await api.get<OnboardingStep[]>("/onboarding/");
    return mapOnboardingSteps(response.data);
  },
};

export const settingsService = {
  async getProfile() {
    const response = await api.get<SettingsProfile>("/settings/");
    return mapSettingsProfile(response.data);
  },

  async updateProfile(payload: SettingsProfile) {
    const response = await api.patch<SettingsProfile>("/settings/", payload);
    return mapSettingsProfile(response.data);
  },
};

export const organizationsService = {
  async list() {
    const response = await api.get<OrganizationSummary[]>("/organizations/");
    return response.data;
  },
};

export const legalService = {
  async getStatus() {
    const response = await api.get<LegalAcceptanceStatus>("/legal/profile/status/");
    return response.data;
  },

  async accept(payload: {
    document_keys: string[];
    source: "registration" | "settings" | "billing" | "onboarding";
  }) {
    const response = await api.post<LegalAcceptanceStatus>("/legal/profile/accept/", payload);
    return response.data;
  },
};

export interface WhatsAppAccount {
  id: number;
  phone_number_id: string;
  display_number: string;
  business_account_id: string;
  status: string;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export const whatsappService = {
  async listAccounts() {
    const response = await api.get<WhatsAppAccount[]>("/whatsapp/accounts/");
    return response.data;
  },
};

export const organizationApiKeysService = {
  async list(includeInactive: boolean) {
    const response = await api.get<OrganizationApiKeyRow[]>("/organization-api-keys/", {
      params: includeInactive ? { includeInactive: true } : undefined,
    });
    return response.data;
  },

  async create(payload: CreateOrganizationApiKeyInput) {
    const response = await api.post<CreateOrganizationApiKeyResponse>(
      "/organization-api-keys/",
      payload
    );
    return response.data;
  },

  async revoke(id: number) {
    await api.post(`/organization-api-keys/${id}/revoke/`);
  },

  async rotate(id: number) {
    const response = await api.post<CreateOrganizationApiKeyResponse>(
      `/organization-api-keys/${id}/rotate/`
    );
    return response.data;
  },

  async auditEvents(id: number) {
    const response = await api.get<OrganizationApiKeyAuditEvent[]>(
      `/organization-api-keys/${id}/audit-events/`
    );
    return response.data;
  },
};
