import { api } from "@/lib/api";
import type {
  AnalyticsSnapshot,
  AuthUser,
  BillingSnapshot,
  DashboardOverview,
  IntegrationItem,
  OnboardingStep,
  RecordItem,
  SettingsProfile,
} from "@/types/platform";

export const authService = {
  async login(email: string, password: string) {
    const response = await api.post<{ user: AuthUser }>("/mock/auth/login", { email, password });
    return response.data.user;
  },

  async register(payload: { name: string; company: string; email: string; password: string }) {
    const response = await api.post<{ user: AuthUser }>("/mock/auth/register", payload);
    return response.data.user;
  },

  async forgotPassword(email: string) {
    const response = await api.post<{ status: string }>("/mock/auth/forgot-password", { email });
    return response.data;
  },

  async completeOnboarding(userId: string) {
    const response = await api.post<{ user: AuthUser }>("/mock/onboarding/complete", { userId });
    return response.data.user;
  },

  async loginWithGoogle() {
    const response = await api.post<{ user: AuthUser }>("/mock/auth/google");
    return response.data.user;
  },
};

export const dashboardService = {
  async getOverview() {
    const response = await api.get<DashboardOverview>("/mock/dashboard");
    return response.data;
  },
};

export const recordsService = {
  async list() {
    const response = await api.get<RecordItem[]>("/mock/records");
    return response.data;
  },
};

export const analyticsService = {
  async getSnapshot() {
    const response = await api.get<AnalyticsSnapshot>("/mock/analytics");
    return response.data;
  },
};

export const integrationsService = {
  async list() {
    const response = await api.get<IntegrationItem[]>("/mock/integrations");
    return response.data;
  },

  async testConnection(payload: { id: string; secret?: string; endpoint?: string }) {
    const response = await api.post<{ status: string; maskedSecret?: string }>(
      "/mock/integrations/test",
      payload
    );
    return response.data;
  },
};

export const billingService = {
  async getSnapshot() {
    const response = await api.get<BillingSnapshot>("/mock/billing");
    return response.data;
  },

  async checkout(payload: { plan: string }) {
    const response = await api.post<{ status: string; checkoutUrl: string }>(
      "/mock/billing/checkout",
      payload
    );
    return response.data;
  },
};

export const onboardingService = {
  async getSteps() {
    const response = await api.get<OnboardingStep[]>("/mock/onboarding");
    return response.data;
  },
};

export const settingsService = {
  async getProfile() {
    const response = await api.get<SettingsProfile>("/mock/settings");
    return response.data;
  },
};
