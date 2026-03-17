export type SupportedCurrency = "USD" | "EUR" | "GBP" | "KES" | "INR";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  company: string;
  role: "owner" | "operator";
  onboardingCompleted: boolean;
}

export interface DashboardMetric {
  label: string;
  value: string;
  delta: string;
  tone: "positive" | "neutral";
}

export interface ProcessingActivity {
  id: string;
  customer: string;
  transcriptSnippet: string;
  status: "processed" | "review" | "failed";
  createdAt: string;
}

export interface DashboardOverview {
  metrics: DashboardMetric[];
  activities: ProcessingActivity[];
}

export interface RecordItem {
  id: string;
  date: string;
  customer: string;
  product: string;
  quantity: number;
  amount: number;
  currency: SupportedCurrency;
  paymentMethod: string;
  transcript: string;
  confidenceScore: number;
}

export interface AnalyticsSeriesPoint {
  label: string;
  value: number;
}

export interface AnalyticsSnapshot {
  salesPerDay: AnalyticsSeriesPoint[];
  salesPerProduct: AnalyticsSeriesPoint[];
  revenueTrends: AnalyticsSeriesPoint[];
  processingStats: AnalyticsSeriesPoint[];
  heatmapSummary: string[];
}

export interface IntegrationItem {
  id: string;
  name: string;
  description: string;
  status: "connected" | "attention" | "available";
  lastSync: string;
  endpoint?: string;
  maskedSecret?: string;
}

export interface Invoice {
  id: string;
  amount: number;
  currency: SupportedCurrency;
  status: "paid" | "due";
  issuedAt: string;
}

export interface SubscriptionSnapshot {
  plan: string;
  amount: number;
  currency: SupportedCurrency;
  seats: number;
  voiceNotesProcessed: number;
  includedVoiceNotes: number;
  renewalDate: string;
}

export interface BillingSnapshot {
  subscription: SubscriptionSnapshot;
  invoices: Invoice[];
}

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

export interface SettingsProfile {
  company: string;
  contactEmail: string;
  timezone: string;
  defaultLanguage: string;
  defaultCurrency: SupportedCurrency;
}
