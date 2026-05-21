"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ExternalLink, Loader2, MessageCircle, ShieldCheck } from "lucide-react";

import { PlanCatalogGrid } from "@/components/billing/plan-catalog-grid";
import { PlanChangeModal } from "@/components/billing/plan-change-modal";
import { BrowserVoiceRecorder } from "@/components/records/browser-voice-recorder";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { legalService, settingsService, whatsappService } from "@/services/platform-service";
import { useLegalStatus, LEGAL_STATUS_QUERY_KEY } from "@/shared/hooks/use-legal-status";
import { ONBOARDING_STEPS_QUERY_KEY, useOnboardingSnapshot } from "@/shared/hooks/use-onboarding";
import { usePlans } from "@/shared/hooks/use-plans";
import { invalidateBillingQueries } from "@/shared/hooks/use-change-plan";
import { trackEvent } from "@/lib/analytics";
import type { PlanChangeKind } from "@/lib/plan-display";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { toast } from "@/shared/hooks/use-toast";
import { notifyApiError } from "@/shared/lib/notify-api-error";
import { cn } from "@/shared/lib/utils";
import type { BillingInterval, PlanCatalogItem, SettingsProfile } from "@/types/platform";

type OnboardingTabId = "legal" | "company" | "plan" | "whatsapp" | "voice" | "confirm" | "complete";

const TAB_ORDER: OnboardingTabId[] = ["legal", "company", "plan", "whatsapp", "voice", "confirm"];

const TAB_LABELS: Record<OnboardingTabId, string> = {
  legal: "Legal",
  company: "Company",
  plan: "Plan",
  whatsapp: "WhatsApp",
  voice: "Voice",
  confirm: "Confirm",
  complete: "Done",
};

const OPTIONAL_TABS = new Set<OnboardingTabId>(["whatsapp", "voice"]);

function stepById(steps: ReturnType<typeof useOnboardingSnapshot>["steps"], id: string) {
  return steps.find((step) => step.id === id);
}

export function OnboardingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { completeOnboarding, isLoading: isAuthLoading, user } = useAuth();
  const snapshot = useOnboardingSnapshot();
  const legal = useLegalStatus();

  const [activeTab, setActiveTab] = useState<OnboardingTabId>("legal");
  const [skippedTabs, setSkippedTabs] = useState<Set<OnboardingTabId>>(() => new Set());

  const [voiceDataConsent, setVoiceDataConsent] = useState(false);
  const [aiReviewAcknowledged, setAiReviewAcknowledged] = useState(false);
  const [recordVerificationAcknowledged, setRecordVerificationAcknowledged] = useState(false);
  const [error, setError] = useState("");

  const reasonParam = searchParams?.get("reason");
  const showLegalForced = reasonParam === "legal-required";

  const companyComplete = stepById(snapshot.steps, "company-setup")?.completed ?? false;
  const planComplete = stepById(snapshot.steps, "choose-plan")?.completed ?? false;
  const whatsappComplete = stepById(snapshot.steps, "connect-whatsapp")?.completed ?? false;
  const voiceComplete = stepById(snapshot.steps, "first-voice-note")?.completed ?? false;

  const furthestTab = useMemo((): OnboardingTabId => {
    if (!legal.isSignupCompliant) return "legal";
    if (user?.onboardingCompleted) return "complete";
    if (!companyComplete) return "company";
    if (!planComplete) return "plan";
    if (!whatsappComplete && !skippedTabs.has("whatsapp")) return "whatsapp";
    if (!voiceComplete && !skippedTabs.has("voice")) return "voice";
    if (snapshot.requiredStepsComplete) return "confirm";
    return "plan";
  }, [
    legal.isSignupCompliant,
    user?.onboardingCompleted,
    companyComplete,
    planComplete,
    whatsappComplete,
    voiceComplete,
    skippedTabs,
    snapshot.requiredStepsComplete,
  ]);

  useEffect(() => {
    setActiveTab((current) => {
      const currentIndex = TAB_ORDER.indexOf(current);
      const furthestIndex = TAB_ORDER.indexOf(furthestTab);
      if (furthestIndex > currentIndex) return furthestTab;
      return current;
    });
  }, [furthestTab]);

  const acceptLegalMutation = useMutation({
    mutationFn: () =>
      legalService.accept({
        document_keys: legal.missingSignup,
        source: "onboarding",
      }),
    onSuccess: (next) => {
      queryClient.setQueryData(LEGAL_STATUS_QUERY_KEY, next);
      toast({ title: "Legal acceptance recorded" });
      trackEvent("onboarding_legal_accepted", {});
      setActiveTab("company");
    },
    onError: (caughtError) => notifyApiError(caughtError, { title: "Could not save acceptance" }),
  });

  useEffect(() => {
    const checkoutResult = searchParams?.get("checkout");
    if (!checkoutResult) return;

    if (checkoutResult === "success") {
      toast({
        title: "Subscription updated",
        description: "Your plan will appear in a moment.",
      });
      invalidateBillingQueries(queryClient);
      void queryClient.invalidateQueries({ queryKey: ONBOARDING_STEPS_QUERY_KEY });
      trackEvent("billing_checkout_returned", { result: "success", context: "onboarding" });
      setActiveTab("plan");
    } else {
      toast({
        title: "Checkout cancelled",
        description: "No changes were made to your subscription.",
        variant: "destructive",
      });
      trackEvent("billing_checkout_returned", { result: "cancelled", context: "onboarding" });
    }

    router.replace("/onboarding");
  }, [searchParams, queryClient, router]);

  const goToNextTab = useCallback(() => {
    const index = TAB_ORDER.indexOf(activeTab);
    const next = TAB_ORDER[index + 1];
    if (next) setActiveTab(next);
  }, [activeTab]);

  const skipOptionalTab = useCallback(() => {
    if (!OPTIONAL_TABS.has(activeTab)) return;
    setSkippedTabs((prev) => new Set(prev).add(activeTab));
    goToNextTab();
  }, [activeTab, goToNextTab]);

  function canNavigateToTab(tab: OnboardingTabId): boolean {
    if (tab === "complete") return user?.onboardingCompleted ?? false;
    const tabIndex = TAB_ORDER.indexOf(tab);
    const furthestIndex = TAB_ORDER.indexOf(furthestTab);
    return tabIndex <= furthestIndex;
  }

  async function finishOnboarding() {
    if (!voiceDataConsent || !aiReviewAcknowledged || !recordVerificationAcknowledged) {
      setError("Confirm each acknowledgement before continuing.");
      return;
    }

    trackEvent("onboarding_step_completed", { step: "attestations" });
    setError("");
    try {
      await completeOnboarding({
        voiceDataConsent,
        aiReviewAcknowledged,
        recordVerificationAcknowledged,
      });
      toast({ title: "Onboarding complete", description: "Welcome to Talk2Record." });
      router.push("/dashboard");
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Unable to complete onboarding."
      );
    }
  }

  const titleByTab: Record<OnboardingTabId, string> = {
    legal: "Accept our legal terms to continue",
    company: "Set up your company profile",
    plan: "Choose a subscription plan",
    whatsapp: "Connect WhatsApp",
    voice: "Send your first voice note",
    confirm: "Confirm responsibilities",
    complete: "You're all set",
  };

  const descriptionByTab: Record<OnboardingTabId, string> = {
    legal:
      "We need your explicit acceptance of the documents below before we can give you access to your workspace.",
    company: "Confirm your workspace name, timezone, and billing currency.",
    plan: "Pick a plan to activate your workspace. You will complete payment securely via Paddle.",
    whatsapp:
      "Optional — connect your business WhatsApp number so Talk2Record can ingest voice notes.",
    voice: "Optional — send a voice note via WhatsApp or record one directly in your browser.",
    confirm: "Last step. Confirm you understand how Talk2Record handles voice data.",
    complete: "Onboarding is done. You can leave this page at any time.",
  };

  return (
    <Card className="border-primary/10 w-full max-w-3xl shadow-(--shadow-lg)">
      <CardHeader>
        <div className="bg-primary/10 text-primary inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
          Guided setup
        </div>
        <CardTitle>{titleByTab[activeTab]}</CardTitle>
        <CardDescription>{descriptionByTab[activeTab]}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <OnboardingTabBar
          activeTab={activeTab}
          furthestTab={furthestTab}
          steps={snapshot.steps}
          skippedTabs={skippedTabs}
          legalComplete={legal.isSignupCompliant}
          onSelectTab={(tab) => {
            if (canNavigateToTab(tab)) setActiveTab(tab);
          }}
        />

        {showLegalForced && activeTab === "legal" ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
            Accept the documents below to access your dashboard.
          </div>
        ) : null}

        {activeTab === "legal" ? (
          <LegalAcceptanceStage
            missingSignup={legal.missingSignup}
            isLoading={legal.isLoading}
            onAccept={() => acceptLegalMutation.mutate()}
            isPending={acceptLegalMutation.isPending}
          />
        ) : null}

        {activeTab === "company" ? (
          <CompanySetupStage onSaved={() => setActiveTab("plan")} />
        ) : null}

        {activeTab === "plan" ? (
          <ChoosePlanStage
            onPlanActive={() => setActiveTab("whatsapp")}
            planComplete={planComplete}
          />
        ) : null}

        {activeTab === "whatsapp" ? (
          <WhatsAppSetupStage
            completed={whatsappComplete}
            onSkip={skipOptionalTab}
            onContinue={goToNextTab}
          />
        ) : null}

        {activeTab === "voice" ? (
          <VoiceNoteStage
            completed={voiceComplete}
            onSkip={skipOptionalTab}
            onContinue={goToNextTab}
          />
        ) : null}

        {activeTab === "confirm" ? (
          <ConfirmStage
            error={error}
            isAuthLoading={isAuthLoading}
            voiceDataConsent={voiceDataConsent}
            aiReviewAcknowledged={aiReviewAcknowledged}
            recordVerificationAcknowledged={recordVerificationAcknowledged}
            onVoiceDataConsent={setVoiceDataConsent}
            onAiReviewAcknowledged={setAiReviewAcknowledged}
            onRecordVerificationAcknowledged={setRecordVerificationAcknowledged}
            onSubmit={finishOnboarding}
          />
        ) : null}

        {activeTab === "complete" ? (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              Onboarding is complete. Open the dashboard to start reviewing extracted records.
            </p>
            <Button className="w-full rounded-xl" onClick={() => router.push("/dashboard")}>
              Open dashboard
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

interface OnboardingTabBarProps {
  activeTab: OnboardingTabId;
  furthestTab: OnboardingTabId;
  steps: ReturnType<typeof useOnboardingSnapshot>["steps"];
  skippedTabs: Set<OnboardingTabId>;
  legalComplete: boolean;
  onSelectTab: (_tab: OnboardingTabId) => void;
}

function OnboardingTabBar({
  activeTab,
  furthestTab,
  steps,
  skippedTabs,
  legalComplete,
  onSelectTab,
}: OnboardingTabBarProps) {
  const furthestIndex = TAB_ORDER.indexOf(furthestTab);

  function isTabComplete(tab: OnboardingTabId): boolean {
    if (tab === "legal") return legalComplete;
    if (tab === "company") return stepById(steps, "company-setup")?.completed ?? false;
    if (tab === "plan") return stepById(steps, "choose-plan")?.completed ?? false;
    if (tab === "whatsapp") return stepById(steps, "connect-whatsapp")?.completed ?? false;
    if (tab === "voice") return stepById(steps, "first-voice-note")?.completed ?? false;
    if (tab === "confirm") return false;
    return false;
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {TAB_ORDER.map((tab) => {
        const index = TAB_ORDER.indexOf(tab);
        const isActive = tab === activeTab;
        const isComplete = isTabComplete(tab) || skippedTabs.has(tab);
        const isDisabled = index > furthestIndex;
        const isOptional = OPTIONAL_TABS.has(tab);

        return (
          <button
            key={tab}
            type="button"
            disabled={isDisabled}
            onClick={() => onSelectTab(tab)}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
              isActive
                ? "bg-primary/15 text-primary"
                : isComplete
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                  : "border-primary/10 text-muted-foreground border",
              isDisabled && "cursor-not-allowed opacity-50"
            )}
          >
            {isComplete ? <CheckCircle2 className="h-3.5 w-3.5" /> : null}
            {TAB_LABELS[tab]}
            {isOptional ? (
              <span className="text-muted-foreground text-[10px] font-normal">(optional)</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function CompanySetupStage({ onSaved }: { onSaved: () => void }) {
  const queryClient = useQueryClient();
  const profileQuery = useQuery({
    queryKey: ["settings-profile"],
    queryFn: settingsService.getProfile,
  });
  const [draft, setDraft] = useState<SettingsProfile | null>(null);

  const saveProfile = useMutation({
    mutationFn: settingsService.updateProfile,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ONBOARDING_STEPS_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: ["settings-profile"] });
      toast({ title: "Company profile saved" });
      trackEvent("onboarding_step_completed", { step: "company-setup" });
      onSaved();
    },
    onError: (caughtError) => notifyApiError(caughtError, { title: "Could not save profile" }),
  });

  const form = draft ?? profileQuery.data;

  if (profileQuery.isLoading || !form) {
    return (
      <div className="border-primary/10 flex items-center gap-2 rounded-2xl border p-4 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading company profile…
      </div>
    );
  }

  return (
    <div className="border-primary/10 space-y-4 rounded-2xl border p-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="onboarding-company">Company</Label>
          <Input
            id="onboarding-company"
            value={form.company}
            onChange={(event) => setDraft({ ...form, company: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="onboarding-email">Contact email</Label>
          <Input
            id="onboarding-email"
            value={form.contactEmail}
            onChange={(event) => setDraft({ ...form, contactEmail: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="onboarding-timezone">Timezone</Label>
          <Input
            id="onboarding-timezone"
            value={form.timezone}
            onChange={(event) => setDraft({ ...form, timezone: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="onboarding-currency">Default currency</Label>
          <Input
            id="onboarding-currency"
            value={form.defaultCurrency}
            onChange={(event) =>
              setDraft({
                ...form,
                defaultCurrency: event.target.value as SettingsProfile["defaultCurrency"],
              })
            }
          />
        </div>
      </div>
      <Button
        className="rounded-xl"
        disabled={saveProfile.isPending}
        onClick={() => saveProfile.mutate(form)}
      >
        {saveProfile.isPending ? "Saving…" : "Save and continue"}
      </Button>
    </div>
  );
}

function ChoosePlanStage({
  onPlanActive,
  planComplete,
}: {
  onPlanActive: () => void;
  planComplete: boolean;
}) {
  const queryClient = useQueryClient();
  const { plans, isLoading } = usePlans();
  const [selectedPlan, setSelectedPlan] = useState<PlanCatalogItem | null>(null);
  const [changeKind, setChangeKind] = useState<PlanChangeKind>("new");
  const checkoutSuccessUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/onboarding?checkout=success`
      : undefined;

  useEffect(() => {
    if (planComplete) onPlanActive();
  }, [planComplete, onPlanActive]);

  const [selectedInterval, setSelectedInterval] = useState<BillingInterval>("month");

  function openPlan(plan: PlanCatalogItem, kind: PlanChangeKind, interval: BillingInterval) {
    setSelectedPlan(plan);
    setChangeKind(kind);
    setSelectedInterval(interval);
  }

  return (
    <div className="space-y-4">
      {planComplete ? (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-800 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Your subscription is active. Continue to the next step.
        </div>
      ) : null}
      <PlanCatalogGrid
        plans={plans}
        isLoading={isLoading}
        variant="billing"
        onSelectPlan={openPlan}
      />
      <PlanChangeModal
        open={selectedPlan !== null}
        plan={selectedPlan}
        changeKind={changeKind}
        interval={selectedInterval}
        successUrl={checkoutSuccessUrl}
        onOpenChange={(open) => {
          if (!open) setSelectedPlan(null);
        }}
      />
      {planComplete ? (
        <Button className="rounded-xl" onClick={onPlanActive}>
          Continue to WhatsApp
        </Button>
      ) : (
        <Button
          variant="outline"
          className="rounded-xl"
          onClick={() =>
            void queryClient.invalidateQueries({ queryKey: ONBOARDING_STEPS_QUERY_KEY })
          }
        >
          Refresh plan status
        </Button>
      )}
    </div>
  );
}

function WhatsAppSetupStage({
  completed,
  onSkip,
  onContinue,
}: {
  completed: boolean;
  onSkip: () => void;
  onContinue: () => void;
}) {
  const accountsQuery = useQuery({
    queryKey: ["whatsapp", "accounts"],
    queryFn: () => whatsappService.listAccounts(),
  });

  return (
    <div className="space-y-4">
      <div className="border-primary/10 bg-background/80 rounded-2xl border p-4">
        <div className="flex items-start gap-3">
          <MessageCircle className="text-primary mt-0.5 h-5 w-5 shrink-0" />
          <div className="space-y-2 text-sm">
            <p className="font-medium">Connect WhatsApp Business</p>
            <p className="text-muted-foreground">
              Link your inbound business number in Integrations. Once connected, voice notes sent to
              that number will appear in Talk2Record automatically.
            </p>
            {accountsQuery.isLoading ? (
              <p className="text-muted-foreground">Checking connection status…</p>
            ) : (accountsQuery.data?.length ?? 0) > 0 ? (
              <p className="text-emerald-700 dark:text-emerald-300">
                {accountsQuery.data!.length} WhatsApp account
                {accountsQuery.data!.length === 1 ? "" : "s"} configured.
              </p>
            ) : (
              <p className="text-muted-foreground">No WhatsApp accounts connected yet.</p>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button asChild className="rounded-xl">
          <Link href="/dashboard/integrations">
            Open integrations
            <ExternalLink className="ml-1 h-3.5 w-3.5" />
          </Link>
        </Button>
        {completed ? (
          <Button variant="outline" className="rounded-xl" onClick={onContinue}>
            Continue
          </Button>
        ) : (
          <Button variant="ghost" className="rounded-xl" onClick={onSkip}>
            Skip for now
          </Button>
        )}
      </div>
    </div>
  );
}

function VoiceNoteStage({
  completed,
  onSkip,
  onContinue,
}: {
  completed: boolean;
  onSkip: () => void;
  onContinue: () => void;
}) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!completed) return;
    const timer = window.setTimeout(onContinue, 800);
    return () => window.clearTimeout(timer);
  }, [completed, onContinue]);

  return (
    <div className="space-y-4">
      {completed ? (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-800 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Voice note received. Moving to confirmation…
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="border-primary/10 space-y-3 rounded-2xl border p-4">
          <p className="text-sm font-medium">Via WhatsApp</p>
          <p className="text-muted-foreground text-sm">
            Send a voice note to your connected WhatsApp business number. We will detect it
            automatically.
          </p>
          <Button asChild variant="outline" size="sm" className="rounded-xl">
            <Link href="/dashboard/integrations">Check WhatsApp setup</Link>
          </Button>
        </div>

        <BrowserVoiceRecorder
          onUploaded={() => {
            trackEvent("onboarding_step_completed", {
              step: "first-voice-note",
              source: "browser",
            });
            void queryClient.invalidateQueries({ queryKey: ONBOARDING_STEPS_QUERY_KEY });
          }}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          className="rounded-xl"
          onClick={() =>
            void queryClient.invalidateQueries({ queryKey: ONBOARDING_STEPS_QUERY_KEY })
          }
        >
          Check for voice notes
        </Button>
        {completed ? (
          <Button className="rounded-xl" onClick={onContinue}>
            Continue
          </Button>
        ) : (
          <Button variant="ghost" className="rounded-xl" onClick={onSkip}>
            Skip for now
          </Button>
        )}
      </div>
    </div>
  );
}

function ConfirmStage({
  error,
  isAuthLoading,
  voiceDataConsent,
  aiReviewAcknowledged,
  recordVerificationAcknowledged,
  onVoiceDataConsent,
  onAiReviewAcknowledged,
  onRecordVerificationAcknowledged,
  onSubmit,
}: {
  error: string;
  isAuthLoading: boolean;
  voiceDataConsent: boolean;
  aiReviewAcknowledged: boolean;
  recordVerificationAcknowledged: boolean;
  onVoiceDataConsent: (_value: boolean) => void;
  onAiReviewAcknowledged: (_value: boolean) => void;
  onRecordVerificationAcknowledged: (_value: boolean) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="border-primary/10 bg-background/80 rounded-2xl border p-4">
        <p className="text-sm font-medium">Before we mark you complete</p>
        <div className="text-muted-foreground mt-3 space-y-3 text-sm">
          <label className="flex items-start gap-3">
            <input
              checked={voiceDataConsent}
              className="border-primary/20 mt-1 h-4 w-4 rounded"
              onChange={(event) => onVoiceDataConsent(event.target.checked)}
              type="checkbox"
            />
            <span>You confirm you have consent to process voice data from your customers.</span>
          </label>
          <label className="flex items-start gap-3">
            <input
              checked={aiReviewAcknowledged}
              className="border-primary/20 mt-1 h-4 w-4 rounded"
              onChange={(event) => onAiReviewAcknowledged(event.target.checked)}
              type="checkbox"
            />
            <span>You understand AI outputs may not be 100% accurate.</span>
          </label>
          <label className="flex items-start gap-3">
            <input
              checked={recordVerificationAcknowledged}
              className="border-primary/20 mt-1 h-4 w-4 rounded"
              onChange={(event) => onRecordVerificationAcknowledged(event.target.checked)}
              type="checkbox"
            />
            <span>You are responsible for verifying records before operational use.</span>
          </label>
        </div>
      </div>
      {error ? <p className="text-destructive text-sm">{error}</p> : null}
      <Button className="w-full rounded-xl" disabled={isAuthLoading} onClick={onSubmit}>
        Finalize onboarding
      </Button>
    </div>
  );
}

interface LegalAcceptanceStageProps {
  missingSignup: string[];
  isLoading: boolean;
  onAccept: () => void;
  isPending: boolean;
}

function LegalAcceptanceStage({
  missingSignup,
  isLoading,
  onAccept,
  isPending,
}: LegalAcceptanceStageProps) {
  const [agreed, setAgreed] = useState(false);

  if (isLoading) {
    return <p className="text-muted-foreground text-sm">Loading required documents…</p>;
  }

  if (missingSignup.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        We could not load the list of required documents. Refresh the page or contact support if
        this persists.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="border-primary/10 bg-background/80 rounded-2xl border p-4">
        <div className="flex items-start gap-3">
          <ShieldCheck className="text-primary mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="text-sm font-medium">Documents you need to accept</p>
            <ul className="text-muted-foreground mt-2 list-disc space-y-1 pl-5 text-sm">
              {missingSignup.map((key) => (
                <li key={key}>
                  <a
                    className="text-primary hover:underline"
                    href={`/legal/${key}`}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {prettyDocumentLabel(key)}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <label className="border-primary/10 bg-background/80 flex items-start gap-3 rounded-xl border p-3 text-sm">
        <input
          checked={agreed}
          className="border-primary/20 mt-1 h-4 w-4 rounded"
          onChange={(event) => setAgreed(event.target.checked)}
          type="checkbox"
        />
        <span className="text-muted-foreground">
          I have read and accept the documents listed above.
        </span>
      </label>
      <Button
        className="w-full rounded-xl"
        disabled={!agreed || isPending}
        onClick={() => onAccept()}
      >
        {isPending ? "Recording acceptance…" : "Accept and continue"}
      </Button>
    </div>
  );
}

function prettyDocumentLabel(key: string): string {
  return key
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
