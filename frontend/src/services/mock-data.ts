import type {
  AnalyticsSnapshot,
  BillingSnapshot,
  DashboardOverview,
  IntegrationItem,
  OnboardingStep,
  RecordItem,
  SettingsProfile,
} from "@/types/platform";

export const dashboardOverview: DashboardOverview = {
  metrics: [
    { label: "Voice notes processed", value: "1,284", delta: "+18% this week", tone: "positive" },
    { label: "Revenue captured", value: "$42.8k", delta: "+9% vs last week", tone: "positive" },
    { label: "Review queue", value: "26", delta: "4 need attention", tone: "neutral" },
    { label: "Active operators", value: "14", delta: "2 onboarding now", tone: "neutral" },
  ],
  activities: [
    {
      id: "act_1",
      customer: "Kifaru Wholesalers",
      transcriptSnippet: "Received twelve cartons of cooking oil, cash on delivery.",
      status: "processed",
      createdAt: "2026-03-17T09:14:00.000Z",
    },
    {
      id: "act_2",
      customer: "Maua Retail",
      transcriptSnippet: "Transfer confirmed for five bags of rice, please log delivery.",
      status: "review",
      createdAt: "2026-03-17T08:42:00.000Z",
    },
    {
      id: "act_3",
      customer: "Jirani Stores",
      transcriptSnippet: "Stock adjustment note could not be confidently classified.",
      status: "failed",
      createdAt: "2026-03-17T07:58:00.000Z",
    },
  ],
};

export const records: RecordItem[] = [
  {
    id: "rec_1",
    date: "2026-03-17T09:14:00.000Z",
    customer: "Kifaru Wholesalers",
    product: "Cooking Oil Carton",
    quantity: 12,
    amount: 18600,
    currency: "KES",
    paymentMethod: "Cash",
    transcript: "Received twelve cartons of cooking oil, cash on delivery.",
    confidenceScore: 0.96,
  },
  {
    id: "rec_2",
    date: "2026-03-16T15:21:00.000Z",
    customer: "Maua Retail",
    product: "Rice Bag 25kg",
    quantity: 5,
    amount: 9450,
    currency: "KES",
    paymentMethod: "Bank transfer",
    transcript: "Transfer confirmed for five bags of rice, deliver tomorrow morning.",
    confidenceScore: 0.91,
  },
  {
    id: "rec_3",
    date: "2026-03-15T13:00:00.000Z",
    customer: "Palm Foods",
    product: "Detergent Bundle",
    quantity: 18,
    amount: 1220,
    currency: "USD",
    paymentMethod: "Card",
    transcript: "Eighteen detergent bundles paid by card for branch restock.",
    confidenceScore: 0.88,
  },
  {
    id: "rec_4",
    date: "2026-03-14T11:33:00.000Z",
    customer: "Urban Mart",
    product: "Soft Drink Crate",
    quantity: 8,
    amount: 640,
    currency: "GBP",
    paymentMethod: "Cash",
    transcript: "Eight soft drink crates sold on cash, include weekend promo note.",
    confidenceScore: 0.93,
  },
];

export const analyticsSnapshot: AnalyticsSnapshot = {
  salesPerDay: [
    { label: "Mon", value: 24 },
    { label: "Tue", value: 30 },
    { label: "Wed", value: 28 },
    { label: "Thu", value: 35 },
    { label: "Fri", value: 41 },
    { label: "Sat", value: 38 },
    { label: "Sun", value: 22 },
  ],
  salesPerProduct: [
    { label: "Cooking Oil", value: 46 },
    { label: "Rice", value: 34 },
    { label: "Detergent", value: 27 },
    { label: "Soft Drinks", value: 31 },
  ],
  revenueTrends: [
    { label: "Jan", value: 18000 },
    { label: "Feb", value: 24000 },
    { label: "Mar", value: 31000 },
    { label: "Apr", value: 36500 },
  ],
  processingStats: [
    { label: "Processed", value: 88 },
    { label: "Review", value: 9 },
    { label: "Failed", value: 3 },
  ],
  heatmapSummary: [
    "Most clicks happen on the records table filters and integration test buttons.",
    "Users pause most often at the WhatsApp connection step in onboarding.",
    "Billing plan comparisons drive the highest conversion interactions.",
  ],
};

export const integrations: IntegrationItem[] = [
  {
    id: "whatsapp",
    name: "WhatsApp",
    description: "Receive and parse inbound business voice notes.",
    status: "connected",
    lastSync: "2 minutes ago",
    endpoint: "wa.me/talk2record-demo",
  },
  {
    id: "stripe",
    name: "Stripe",
    description: "Route subscription checkout through Stripe.",
    status: "connected",
    lastSync: "15 minutes ago",
    maskedSecret: "sk_live_***89d1",
  },
  {
    id: "paddle",
    name: "Paddle",
    description: "Alternative billing provider for international checkout.",
    status: "available",
    lastSync: "Never",
  },
  {
    id: "google-sheets",
    name: "Google Sheets",
    description: "Push structured records into finance and ops sheets.",
    status: "attention",
    lastSync: "3 days ago",
  },
  {
    id: "zapier",
    name: "Zapier",
    description: "Trigger automations when new records are extracted.",
    status: "available",
    lastSync: "Never",
  },
  {
    id: "webhooks",
    name: "Webhooks",
    description: "Send record events to downstream internal systems.",
    status: "connected",
    lastSync: "1 hour ago",
    endpoint: "https://example.com/hooks/talk2record",
  },
];

export const billingSnapshot: BillingSnapshot = {
  subscription: {
    plan: "Growth",
    amount: 99,
    currency: "USD",
    seats: 14,
    voiceNotesProcessed: 1284,
    includedVoiceNotes: 2000,
    renewalDate: "2026-04-01T00:00:00.000Z",
  },
  invoices: [
    { id: "inv_3103", amount: 99, currency: "USD", status: "paid", issuedAt: "2026-03-01T00:00:00.000Z" },
    { id: "inv_2802", amount: 99, currency: "USD", status: "paid", issuedAt: "2026-02-01T00:00:00.000Z" },
    { id: "inv_0104", amount: 99, currency: "USD", status: "due", issuedAt: "2026-04-01T00:00:00.000Z" }
  ],
};

export const onboardingSteps: OnboardingStep[] = [
  {
    id: "connect-whatsapp",
    title: "Connect WhatsApp",
    description: "Bind your inbound business number to Talk2Record.",
    completed: true,
  },
  {
    id: "first-voice-note",
    title: "Send first voice note",
    description: "Validate extraction on a real staff workflow.",
    completed: false,
  },
  {
    id: "company-setup",
    title: "Set up company details",
    description: "Choose locale, billing currency, and notification defaults.",
    completed: false,
  },
];

export const settingsProfile: SettingsProfile = {
  company: "Talk2Record Demo Workspace",
  contactEmail: "alphanganga@gmail.com",
  timezone: "Africa/Nairobi",
  defaultLanguage: "English",
  defaultCurrency: "USD",
};
