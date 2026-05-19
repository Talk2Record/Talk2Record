import type {
  PlanCatalogItem,
  PlanPriceRow,
  AnalyticsSnapshot,
  AuthUser,
  BillingSnapshot,
  DashboardOverview,
  LegalAcceptanceStatus,
  OnboardingStep,
  RecordArtifact,
  RecordItem,
  RecordStatus,
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

interface BackendRecordArtifact {
  id: number | string;
  kind: string;
  url?: string | null;
  created_at?: string;
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
  status?: string;
  processing_error?: string | null;
  processing_error_step?: string | null;
  processing_retry_count?: number;
  last_failed_at?: string | null;
  dead_lettered_at?: string | null;
  artifacts?: BackendRecordArtifact[];
}

const RECORD_STATUS_VALUES: readonly RecordStatus[] = [
  "received",
  "transcribing",
  "transcribed",
  "extracting",
  "extracted",
  "stored",
  "review",
  "failed",
  "dead_letter",
];

function coerceStatus(value: string | undefined): RecordStatus {
  if (!value) return "received";
  const normalized = value.toLowerCase();
  return (RECORD_STATUS_VALUES as readonly string[]).includes(normalized)
    ? (normalized as RecordStatus)
    : "received";
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

function mapArtifact(artifact: BackendRecordArtifact): RecordArtifact {
  return {
    id: artifact.id,
    kind: artifact.kind,
    url: artifact.url ?? null,
    created_at: artifact.created_at ?? "",
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
    status: coerceStatus(record.status),
    processingError: record.processing_error ?? null,
    processingErrorStep: record.processing_error_step ?? null,
    processingRetryCount: record.processing_retry_count ?? 0,
    lastFailedAt: record.last_failed_at ?? null,
    deadLetteredAt: record.dead_lettered_at ?? null,
    artifacts: (record.artifacts ?? []).map(mapArtifact),
  };
}

export function mapDashboardOverview(snapshot: DashboardOverview): DashboardOverview {
  return snapshot;
}

export function mapAnalyticsSnapshot(snapshot: AnalyticsSnapshot): AnalyticsSnapshot {
  return snapshot;
}


interface BackendPlanPriceRow {
  interval: string;
  amount: number | string;
  currency: string;
  active: boolean;
  trialPeriod?: { interval: string; frequency: number } | null;
}

interface BackendPlanCatalogItem {
  code: string;
  name: string;
  base_price: number | string;
  currency: string;
  region: string;
  features: string[];
  prices: BackendPlanPriceRow[];
  entitlements: Array<{
    feature_key: string;
    enabled: boolean;
    limit: number;
    period: string;
  }>;
  monthly_amount: number | string;
  is_highlighted: boolean;
}

export function mapPlanCatalogItem(plan: BackendPlanCatalogItem): PlanCatalogItem {
  return {
    code: plan.code,
    name: plan.name,
    currency: plan.currency as PlanCatalogItem["currency"],
    basePrice: Number(plan.base_price),
    monthlyPrice: Number(plan.monthly_amount),
    region: plan.region,
    features: plan.features ?? [],
    prices: (plan.prices ?? []).map(
      (price): PlanPriceRow => ({
        interval: price.interval,
        amount: Number(price.amount),
        currency: price.currency as PlanPriceRow["currency"],
        active: price.active,
        trialPeriod: price.trialPeriod ?? null,
      })
    ),
    entitlements: (plan.entitlements ?? []).map((row) => ({
      feature_key: row.feature_key,
      enabled: row.enabled,
      limit: row.limit,
      period: row.period as PlanCatalogItem["entitlements"][number]["period"],
    })),
    isHighlighted: Boolean(plan.is_highlighted),
  };
}

export function mapBillingSnapshot(snapshot: BillingSnapshot): BillingSnapshot {
  return {
    subscription: {
      ...snapshot.subscription,
      amount: Number(snapshot.subscription.amount),
      voiceNotesProcessed: Number(snapshot.subscription.voiceNotesProcessed),
      includedVoiceNotes: Number(snapshot.subscription.includedVoiceNotes),
      seats: Number(snapshot.subscription.seats),
      planCode: snapshot.subscription.planCode ?? null,
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
