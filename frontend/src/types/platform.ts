export type SupportedCurrency = "USD" | "EUR" | "GBP" | "KES" | "INR";

export interface AcceptedLegalDocument {
  documentKey: string;
  version: string;
  acceptedAt: string | null;
}

export interface LegalAcceptanceStatus {
  accepted_documents: AcceptedLegalDocument[];
  required_signup_documents: string[];
  required_billing_documents: string[];
  has_required_signup_acceptance: boolean;
  has_required_billing_acceptance: boolean;
}

export type OrgRole = "owner" | "admin" | "operator";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  company: string;
  role: OrgRole;
  onboardingCompleted: boolean;
  isStaff: boolean;
  isSuperuser: boolean;
  legal: LegalAcceptanceStatus;
}

export interface OrganizationSummary {
  id: number;
  name: string;
  slug: string;
  region?: string;
  timezone: string;
  default_currency: string;
  status: string;
}

export interface MembershipRow {
  id: number;
  organization: OrganizationSummary;
  role: OrgRole;
  status: string;
  joined_at: string;
  userEmail: string;
  userName: string;
}

export interface InvitationRow {
  id: number;
  organization: OrganizationSummary;
  email: string;
  role: OrgRole;
  status: "pending" | "accepted" | "revoked" | "expired";
  invitedByEmail: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface CreateInvitationResponse {
  invitation: InvitationRow;
  acceptUrl: string;
  token: string;
}

export interface SessionRow {
  id: number;
  ip_address: string | null;
  user_agent: string;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  expires_at: string | null;
  isCurrent: boolean;
}

export interface AdminUserRow {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  onboarding_completed: boolean;
  suspended_at: string | null;
  suspended_reason: string;
  date_joined: string;
  last_login: string | null;
  organizationsCount: number;
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

/**
 * Mirrors the backend `Record.Status` enum exactly. Order matters: the
 * pipeline stepper renders steps in this order.
 *
 * Today the Celery pipeline goes `received → transcribing → transcribed →
 * extracting → extracted → stored`. `review` is reserved for manual review
 * workflows; `failed`/`dead_letter` are terminal failure states.
 */
export type RecordStatus =
  | "received"
  | "transcribing"
  | "transcribed"
  | "extracting"
  | "extracted"
  | "stored"
  | "review"
  | "failed"
  | "dead_letter";

export const RECORD_PIPELINE_STEPS = [
  "received",
  "transcribing",
  "extracting",
  "stored",
] as const satisfies readonly RecordStatus[];

export const TERMINAL_RECORD_STATUSES: readonly RecordStatus[] = [
  "stored",
  "failed",
  "dead_letter",
];

export interface RecordArtifact {
  id: string | number;
  kind: string;
  url: string | null;
  created_at: string;
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
  /** Pipeline status mirrored from the backend. */
  status: RecordStatus;
  /** Optional human-readable error message from the pipeline. */
  processingError: string | null;
  /** Pipeline step that failed, when `status` is failed/dead_letter. */
  processingErrorStep: string | null;
  processingRetryCount: number;
  lastFailedAt: string | null;
  deadLetteredAt: string | null;
  artifacts: RecordArtifact[];
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

export interface Invoice {
  id: string;
  amount: number;
  currency: SupportedCurrency;
  status: "paid" | "due";
  issuedAt: string;
}

export type SubscriptionStatus = "trialing" | "active" | "past_due" | "paused" | "canceled";

export interface SubscriptionSnapshot {
  plan: string;
  amount: number;
  currency: SupportedCurrency;
  seats: number;
  voiceNotesProcessed: number;
  includedVoiceNotes: number;
  renewalDate: string;
}

export interface SubscriptionRow {
  id: number;
  plan: string;
  status: SubscriptionStatus;
  amount: number;
  currency: SupportedCurrency;
  seats: number;
  current_period_end: string | null;
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

export type OrganizationApiKeyScopePreset = "ingestion" | "ingestion_plus_read";

export interface OrganizationApiKeyRow {
  id: number;
  name: string;
  scopes: string[];
  is_active: boolean;
  expiresAt: string | null;
  revokedAt: string | null;
  rate_limit_per_minute: number | null;
  lastUsedAt: string | null;
  lastUsedIp: string | null;
  lastUsedUserAgent: string | null;
  created_at: string;
}

export interface CreateOrganizationApiKeyInput {
  name: string;
  scopePreset: OrganizationApiKeyScopePreset;
  expiresInDays?: number;
  rateLimitPerMinute?: number;
}

export interface CreateOrganizationApiKeyResponse {
  apiKey: string;
  key: OrganizationApiKeyRow;
}

export interface OrganizationApiKeyAuditEvent {
  id: number;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
  actorEmail: string | null;
}
