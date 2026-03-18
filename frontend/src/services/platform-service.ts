import { api } from "@/lib/api";
import type {
  AnalyticsSnapshot,
  AuthUser,
  BillingSnapshot,
  DashboardOverview,
  OnboardingStep,
  SettingsProfile,
} from "@/types/platform";
import {
  mapAnalyticsSnapshot,
  mapAuthUser,
  mapBillingSnapshot,
  mapDashboardOverview,
  mapIntegration,
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
};

export const analyticsService = {
  async getSnapshot() {
    const response = await api.get<AnalyticsSnapshot>("/analytics/");
    return mapAnalyticsSnapshot(response.data);
  },
};

export const integrationsService = {
  async list() {
    const response = await api.get<Array<Parameters<typeof mapIntegration>[0]>>("/integrations/");
    return response.data.map(mapIntegration);
  },

  async testConnection(payload: {
    id: string;
    secret?: string;
    endpoint?: string;
    confirmedPermission?: boolean;
  }) {
    const response = await api.post<{ status: string; maskedSecret?: string }>(
      "/integration-actions/test_connection/",
      payload
    );
    return response.data;
  },
};

export const billingService = {
  async getSnapshot() {
    const response = await api.get<BillingSnapshot>("/billing/");
    return mapBillingSnapshot(response.data);
  },

  async checkout(payload: { plan: string; acceptedBillingTerms: boolean }) {
    const response = await api.post<{ status: string; checkoutUrl: string }>(
      "/billing/checkout/",
      payload
    );
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
