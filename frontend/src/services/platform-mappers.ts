import type {
  BillingInterval,
  PlanCatalogItem,
  PlanPriceRow,
  AnalyticsSnapshot,
  AuthUser,
  BillingSnapshot,
  DashboardOverview,
  DetectedCategory,
  DetectedIndustry,
  ExtractedData,
  ExtractionValidationError,
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
  key: string;
  kind?: string;
  artifact_type?: string;
  content?: Record<string, unknown>;
  url?: string | null;
  created_at?: string;
}

interface BackendRecord {
  id: number | string;
  created_at: string;
  customer_name?: string;
  product?: string;
  quantity?: number;
  amount?: number | string;
  currency?: RecordItem["currency"];
  payment_method?: string;
  voice_transcript?: string;
  confidence_score?: number | string;
  status?: string;
  audio_url?: string;
  detected_industries?: unknown;
  detected_categories?: unknown;
  extracted_data?: unknown;
  validation_errors?: unknown;
  processing_step?: string | null;
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
    kind: artifact.key || artifact.kind || "artifact",
    artifactType: artifact.artifact_type ?? "json",
    content: artifact.content ?? null,
    url: artifact.url ?? null,
    created_at: artifact.created_at ?? "",
  };
}

function artifactByKey(
  artifacts: BackendRecordArtifact[],
  key: string
): BackendRecordArtifact | undefined {
  return artifacts.find((artifact) => artifact.key === key);
}

function recordDisplayFields(record: BackendRecord) {
  const artifacts = record.artifacts ?? [];
  const extraction =
    (artifactByKey(artifacts, "extraction")?.content as Record<string, unknown> | undefined) ?? {};
  const transcriptArtifact =
    (artifactByKey(artifacts, "transcript")?.content as Record<string, unknown> | undefined) ?? {};

  const transcriptFromArtifact =
    typeof transcriptArtifact.text === "string" ? transcriptArtifact.text : "";

  return {
    /* Legacy sales-flavored fields are sourced from the legacy artifact
       shape when present; new records may leave them blank. */
    customer: record.customer_name ?? coerceOptionalString(extraction.customer_name),
    product: record.product ?? coerceOptionalString(extraction.product),
    quantity:
      record.quantity ??
      (typeof extraction.quantity === "number" ? extraction.quantity : undefined),
    amount: coerceOptionalNumber(record.amount ?? extraction.amount),
    currency: record.currency ?? (extraction.currency as RecordItem["currency"]) ?? undefined,
    paymentMethod: record.payment_method ?? coerceOptionalString(extraction.payment_method),
    transcript:
      record.voice_transcript ??
      String(extraction.voice_transcript ?? transcriptFromArtifact ?? ""),
    confidenceScore: Number(record.confidence_score ?? 0) || 0,
  };
}

function coerceOptionalString(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function coerceOptionalNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const num = Number(value);
  return Number.isFinite(num) && num !== 0 ? num : undefined;
}

function coerceDetectedIndustries(raw: unknown): DetectedIndustry[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const slug = String((entry as Record<string, unknown>).slug ?? "").trim();
      if (!slug) return null;
      const confidence = Number((entry as Record<string, unknown>).confidence ?? 0);
      return { slug, confidence: Number.isFinite(confidence) ? confidence : 0 };
    })
    .filter((entry): entry is DetectedIndustry => entry !== null);
}

function coerceDetectedCategories(raw: unknown): DetectedCategory[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((entry) => {
      if (!entry || typeof entry !== "object") return null;
      const industry = String((entry as Record<string, unknown>).industry ?? "").trim();
      const slug = String((entry as Record<string, unknown>).slug ?? "").trim();
      if (!slug || !industry) return null;
      const confidence = Number((entry as Record<string, unknown>).confidence ?? 0);
      return {
        industry,
        slug,
        confidence: Number.isFinite(confidence) ? confidence : 0,
      };
    })
    .filter((entry): entry is DetectedCategory => entry !== null);
}

function coerceExtractedData(raw: unknown): ExtractedData {
  if (Array.isArray(raw)) return raw as ExtractedData;
  if (raw && typeof raw === "object") return raw as ExtractedData;
  return {};
}

function coerceValidationErrors(raw: unknown): ExtractionValidationError[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(
      (entry): entry is Record<string, unknown> => entry !== null && typeof entry === "object"
    )
    .map((entry) => ({
      category: typeof entry.category === "string" ? entry.category : undefined,
      path: typeof entry.path === "string" ? entry.path : undefined,
      message: typeof entry.message === "string" ? entry.message : undefined,
      validator: typeof entry.validator === "string" ? entry.validator : undefined,
    }));
}

export function mapRecord(record: BackendRecord): RecordItem {
  const display = recordDisplayFields(record);

  return {
    id: String(record.id),
    date: record.created_at,
    customer: display.customer,
    product: display.product,
    quantity: display.quantity,
    amount: display.amount,
    currency: display.currency,
    paymentMethod: display.paymentMethod,
    transcript: display.transcript,
    confidenceScore: display.confidenceScore,
    status: coerceStatus(record.status),
    audioUrl: record.audio_url ?? "",
    detectedIndustries: coerceDetectedIndustries(record.detected_industries),
    detectedCategories: coerceDetectedCategories(record.detected_categories),
    extractedData: coerceExtractedData(record.extracted_data),
    validationErrors: coerceValidationErrors(record.validation_errors),
    processingStep: record.processing_step ?? "",
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
  const sub = snapshot.subscription;
  // The backend always sends ``usage`` (Phase 2). Guard it anyway so the
  // mapper survives legacy payloads in dev / mocked fixtures.
  const usage = sub.usage ?? {
    featureKey: "ai.usage",
    used: Number(sub.voiceNotesProcessed ?? 0),
    included: Number(sub.includedVoiceNotes ?? 0),
    percentUsed: 0,
    periodStart: sub.renewalDate,
    periodEnd: sub.renewalDate,
  };
  return {
    subscription: {
      ...sub,
      amount: Number(sub.amount),
      voiceNotesProcessed: Number(sub.voiceNotesProcessed),
      includedVoiceNotes: Number(sub.includedVoiceNotes),
      seats: Number(sub.seats),
      planCode: sub.planCode ?? null,
      billingInterval: (sub.billingInterval ?? "month") as BillingInterval,
      trialEndsAt: sub.trialEndsAt ?? null,
      status: sub.status ?? null,
      usage: {
        featureKey: usage.featureKey,
        used: Number(usage.used),
        included: Number(usage.included),
        percentUsed: Number(usage.percentUsed),
        periodStart: usage.periodStart,
        periodEnd: usage.periodEnd,
      },
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
