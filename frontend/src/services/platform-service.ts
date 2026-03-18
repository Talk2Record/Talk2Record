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

const platformApiPrefix = (process.env.NEXT_PUBLIC_PLATFORM_API_PREFIX || "/mock").replace(/\/$/, "");

function platformPath(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${platformApiPrefix}${normalizedPath}`;
}

export const authService = {
  async login(email: string, password: string) {
    const response = await api.post<{ user: AuthUser }>(platformPath("/auth/login"), { email, password });
    return response.data.user;
  },

  async register(payload: {
    name: string;
    company: string;
    email: string;
    password: string;
    acceptedDocumentKeys: string[];
  }) {
    const response = await api.post<{ user: AuthUser }>(platformPath("/auth/register"), payload);
    return response.data.user;
  },

  async forgotPassword(email: string) {
    const response = await api.post<{ status: string }>(platformPath("/auth/forgot-password"), { email });
    return response.data;
  },

  async completeOnboarding(payload: {
    userId: string;
    voiceDataConsent: boolean;
    aiReviewAcknowledged: boolean;
    recordVerificationAcknowledged: boolean;
  }) {
    const response = await api.post<{ user: AuthUser }>(platformPath("/onboarding/complete"), payload);
    return response.data.user;
  },

  async loginWithGoogle() {
    const response = await api.post<{ user: AuthUser }>(platformPath("/auth/google"));
    return response.data.user;
  },
};

export const dashboardService = {
  async getOverview() {
    const response = await api.get<DashboardOverview>(platformPath("/dashboard"));
    return response.data;
  },
};

export const recordsService = {
  async list() {
    const response = await api.get<RecordItem[]>(platformPath("/records"));
    return response.data;
  },
};

export const analyticsService = {
  async getSnapshot() {
    const response = await api.get<AnalyticsSnapshot>(platformPath("/analytics"));
    return response.data;
  },
};

export const integrationsService = {
  async list() {
    const response = await api.get<IntegrationItem[]>(platformPath("/integrations"));
    return response.data;
  },

  async testConnection(payload: {
    id: string;
    secret?: string;
    endpoint?: string;
    confirmedPermission?: boolean;
  }) {
    const response = await api.post<{ status: string; maskedSecret?: string }>(
      platformPath("/integrations/test"),
      payload
    );
    return response.data;
  },
};

export const billingService = {
  async getSnapshot() {
    const response = await api.get<BillingSnapshot>(platformPath("/billing"));
    return response.data;
  },

  async checkout(payload: { plan: string; acceptedBillingTerms: boolean }) {
    const response = await api.post<{ status: string; checkoutUrl: string }>(
      platformPath("/billing/checkout"),
      payload
    );
    return response.data;
  },
};

export const onboardingService = {
  async getSteps() {
    const response = await api.get<OnboardingStep[]>(platformPath("/onboarding"));
    return response.data;
  },
};

export const settingsService = {
  async getProfile() {
    const response = await api.get<SettingsProfile>(platformPath("/settings"));
    return response.data;
  },
};
