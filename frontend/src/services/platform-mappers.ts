import type {
  AnalyticsSnapshot,
  AuthUser,
  BillingSnapshot,
  DashboardOverview,
  LegalAcceptanceStatus,
  OnboardingStep,
  RecordItem,
  SettingsProfile,
} from "@/types/platform";

interface BackendAcceptedDocument {
  documentKey: string;
  version: string;
  acceptedAt: string | null;
}

interface BackendLegalAcceptanceStatus {
  accepted_documents: BackendAcceptedDocument[];
  required_signup_documents: string[];
  required_billing_documents: string[];
  has_required_signup_acceptance: boolean;
  has_required_billing_acceptance: boolean;
}

interface BackendAuthUser {
  id: number | string;
  email: string;
  name: string;
  company: string;
  role: AuthUser["role"];
  onboardingCompleted: boolean;
  isStaff?: boolean;
  isSuperuser?: boolean;
  legal: BackendLegalAcceptanceStatus;
}

interface BackendRecord {
  id: number | string;
  customer_name: string;
  product: string;
  quantity: number;
  amount: number | string;
  currency: RecordItem["currency"];
  payment_method: string;
  voice_transcript: string;
  confidence_score: number | string;
  created_at: string;
}

export function mapLegalAcceptanceStatus(
  legal: BackendLegalAcceptanceStatus
): LegalAcceptanceStatus {
  return {
    accepted_documents: legal.accepted_documents.map((document) => ({
      documentKey: document.documentKey,
      version: document.version,
      acceptedAt: document.acceptedAt,
    })),
    required_signup_documents: legal.required_signup_documents,
    required_billing_documents: legal.required_billing_documents,
    has_required_signup_acceptance: legal.has_required_signup_acceptance,
    has_required_billing_acceptance: legal.has_required_billing_acceptance,
  };
}

export function mapAuthUser(user: BackendAuthUser): AuthUser {
  return {
    id: String(user.id),
    email: user.email,
    name: user.name,
    company: user.company,
    role: user.role,
    onboardingCompleted: user.onboardingCompleted,
    isStaff: Boolean(user.isStaff),
    isSuperuser: Boolean(user.isSuperuser),
    legal: mapLegalAcceptanceStatus(user.legal),
  };
}

export function mapRecord(record: BackendRecord): RecordItem {
  return {
    id: String(record.id),
    date: record.created_at,
    customer: record.customer_name,
    product: record.product,
    quantity: record.quantity,
    amount: Number(record.amount),
    currency: record.currency,
    paymentMethod: record.payment_method,
    transcript: record.voice_transcript,
    confidenceScore: Number(record.confidence_score),
  };
}

export function mapDashboardOverview(snapshot: DashboardOverview): DashboardOverview {
  return snapshot;
}

export function mapAnalyticsSnapshot(snapshot: AnalyticsSnapshot): AnalyticsSnapshot {
  return snapshot;
}

export function mapBillingSnapshot(snapshot: BillingSnapshot): BillingSnapshot {
  return {
    subscription: {
      ...snapshot.subscription,
      amount: Number(snapshot.subscription.amount),
      voiceNotesProcessed: Number(snapshot.subscription.voiceNotesProcessed),
      includedVoiceNotes: Number(snapshot.subscription.includedVoiceNotes),
      seats: Number(snapshot.subscription.seats),
    },
    invoices: snapshot.invoices.map((invoice) => ({
      ...invoice,
      amount: Number(invoice.amount),
    })),
  };
}

export function mapOnboardingSteps(steps: OnboardingStep[]): OnboardingStep[] {
  return steps;
}

export function mapSettingsProfile(profile: SettingsProfile): SettingsProfile {
  return profile;
}
