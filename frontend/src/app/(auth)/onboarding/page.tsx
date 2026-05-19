"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, ExternalLink, ShieldCheck } from "lucide-react";

import { useAuth } from "@/shared/lib/auth/auth-context";
import { legalService } from "@/services/platform-service";
import { useLegalStatus, LEGAL_STATUS_QUERY_KEY } from "@/shared/hooks/use-legal-status";
import { useOnboardingSnapshot } from "@/shared/hooks/use-onboarding";
import { trackEvent } from "@/lib/analytics";
import { getHeatmapAdapter } from "@/lib/heatmap";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { toast } from "@/shared/hooks/use-toast";
import { notifyApiError } from "@/shared/lib/notify-api-error";

/**
 * Onboarding now runs as an explicit three-stage state machine matching the
 * backend:
 *
 *   1. Legal acceptance — blocking. User must accept the required signup
 *      documents before any other step.
 *   2. Step checklist — server-derived. Steps flip automatically when the
 *      backend sees WhatsApp connected, a first voice note arrive, etc.
 *      Users can skip and revisit from the dashboard's OnboardingCard.
 *   3. Final attestations — user confirms voice-data consent, AI-review
 *      acknowledgement, and record verification responsibility. This calls
 *      the backend `complete_onboarding` endpoint.
 *
 * Because steps are derived from real backend signals, we don't fake
 * "Mark complete" buttons; users are deep-linked to the page that triggers
 * the relevant signal (Integrations for WhatsApp, Records for voice notes,
 * Settings for the company profile).
 */
export default function OnboardingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const heatmap = getHeatmapAdapter();
  const { completeOnboarding, isLoading: isAuthLoading, user } = useAuth();
  const snapshot = useOnboardingSnapshot();
  const legal = useLegalStatus();

  const [voiceDataConsent, setVoiceDataConsent] = useState(false);
  const [aiReviewAcknowledged, setAiReviewAcknowledged] = useState(false);
  const [recordVerificationAcknowledged, setRecordVerificationAcknowledged] = useState(false);
  const [error, setError] = useState("");

  const reasonParam = searchParams?.get("reason");
  const showLegalForced = reasonParam === "legal-required";

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
    },
    onError: (caughtError) => notifyApiError(caughtError, { title: "Could not save acceptance" }),
  });

  const stepDestinations: Record<string, { href: string; label: string }> = {
    "connect-whatsapp": {
      href: "/dashboard/integrations",
      label: "Open integrations",
    },
    "first-voice-note": {
      href: "/dashboard/records",
      label: "View records",
    },
    "company-setup": {
      href: "/dashboard/settings",
      label: "Open settings",
    },
  };

  const stage: "legal" | "steps" | "attest" | "complete" = useMemo(() => {
    if (!legal.isSignupCompliant) return "legal";
    if (user?.onboardingCompleted) return "complete";
    if (snapshot.allStepsComplete) return "attest";
    return "steps";
  }, [legal.isSignupCompliant, snapshot.allStepsComplete, user?.onboardingCompleted]);

  async function finishOnboarding() {
    if (!voiceDataConsent || !aiReviewAcknowledged || !recordVerificationAcknowledged) {
      setError("Confirm each acknowledgement before continuing.");
      return;
    }

    heatmap.identifyStep("company-setup");
    trackEvent("onboarding_step_completed", { step: "company-setup" });
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

  // The user landed here from the legal gate. Once they're compliant we
  // surface a small confirmation and let them keep going through the rest of
  // the flow.
  const skip = () => {
    router.push("/dashboard");
  };

  return (
    <Card className="border-primary/10 w-full max-w-2xl shadow-(--shadow-lg)">
      <CardHeader>
        <div className="bg-primary/10 text-primary inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
          Guided setup
        </div>
        <CardTitle>
          {stage === "legal"
            ? "Accept our legal terms to continue"
            : stage === "steps"
              ? "Finish onboarding"
              : stage === "attest"
                ? "Confirm responsibilities"
                : "You're all set"}
        </CardTitle>
        <CardDescription>
          {stage === "legal"
            ? "We need your explicit acceptance of the documents below before we can give you access to your workspace."
            : stage === "steps"
              ? "Complete each item — they automatically tick off as Talk2Record sees the signal."
              : stage === "attest"
                ? "Last step. Confirm you understand how Talk2Record handles voice data."
                : "Onboarding is done. You can leave this page at any time."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <StagePills active={stage} />

        {showLegalForced && stage !== "legal" ? null : null}

        {stage === "legal" ? (
          <LegalAcceptanceStage
            missingSignup={legal.missingSignup}
            onAccept={() => acceptLegalMutation.mutate()}
            isPending={acceptLegalMutation.isPending}
          />
        ) : null}

        {stage === "steps" ? (
          <div className="space-y-3">
            {snapshot.steps.map((step, index) => {
              const destination = stepDestinations[step.id];
              return (
                <div
                  key={step.id}
                  className="border-primary/10 bg-background/80 rounded-2xl border p-4"
                >
                  <div className="flex items-start gap-3">
                    {step.completed ? (
                      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />
                    ) : (
                      <Circle className="text-muted-foreground mt-0.5 h-5 w-5 shrink-0" />
                    )}
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        <span className="text-muted-foreground mr-2">{index + 1}.</span>
                        {step.title}
                      </p>
                      <p className="text-muted-foreground mt-1 text-sm">{step.description}</p>
                      {destination && !step.completed ? (
                        <Button asChild variant="outline" size="sm" className="mt-3 rounded-xl">
                          <a href={destination.href}>
                            {destination.label}
                            <ExternalLink className="ml-1 h-3 w-3" />
                          </a>
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}
            <div className="flex justify-between pt-2">
              <Button type="button" variant="ghost" className="rounded-xl" onClick={skip}>
                Skip for now
              </Button>
              <p className="text-muted-foreground self-end text-xs">
                {snapshot.steps.filter((s) => s.completed).length} of {snapshot.steps.length} done
              </p>
            </div>
          </div>
        ) : null}

        {stage === "attest" ? (
          <div className="space-y-4">
            <div className="border-primary/10 bg-background/80 rounded-2xl border p-4">
              <p className="text-sm font-medium">Before we mark you complete</p>
              <div className="text-muted-foreground mt-3 space-y-3 text-sm">
                <label className="flex items-start gap-3">
                  <input
                    checked={voiceDataConsent}
                    className="border-primary/20 mt-1 h-4 w-4 rounded"
                    onChange={(event) => setVoiceDataConsent(event.target.checked)}
                    type="checkbox"
                  />
                  <span>
                    You confirm you have consent to process voice data from your customers.
                  </span>
                </label>
                <label className="flex items-start gap-3">
                  <input
                    checked={aiReviewAcknowledged}
                    className="border-primary/20 mt-1 h-4 w-4 rounded"
                    onChange={(event) => setAiReviewAcknowledged(event.target.checked)}
                    type="checkbox"
                  />
                  <span>You understand AI outputs may not be 100% accurate.</span>
                </label>
                <label className="flex items-start gap-3">
                  <input
                    checked={recordVerificationAcknowledged}
                    className="border-primary/20 mt-1 h-4 w-4 rounded"
                    onChange={(event) => setRecordVerificationAcknowledged(event.target.checked)}
                    type="checkbox"
                  />
                  <span>You are responsible for verifying records before operational use.</span>
                </label>
              </div>
            </div>
            {error ? <p className="text-destructive text-sm">{error}</p> : null}
            <Button
              className="w-full rounded-xl"
              disabled={isAuthLoading}
              onClick={() => finishOnboarding()}
            >
              Finalize onboarding
            </Button>
          </div>
        ) : null}

        {stage === "complete" ? (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              Onboarding is complete and we no longer need anything from you here. Open the
              dashboard to start reviewing extracted records.
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

/**
 * Tiny breadcrumb-style indicator across the top of the card so the user can
 * see how far they are in the flow at a glance.
 */
function StagePills({ active }: { active: "legal" | "steps" | "attest" | "complete" }) {
  const pills: { id: typeof active; label: string }[] = [
    { id: "legal", label: "Legal" },
    { id: "steps", label: "Setup" },
    { id: "attest", label: "Confirm" },
  ];
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      {pills.map((pill) => {
        const isActive = pill.id === active;
        return (
          <span
            key={pill.id}
            className={
              isActive
                ? "bg-primary/15 text-primary rounded-full px-3 py-1 font-medium"
                : "border-primary/10 text-muted-foreground rounded-full border px-3 py-1"
            }
          >
            {pill.label}
          </span>
        );
      })}
    </div>
  );
}

interface LegalAcceptanceStageProps {
  missingSignup: string[];
  onAccept: () => void;
  isPending: boolean;
}

function LegalAcceptanceStage({ missingSignup, onAccept, isPending }: LegalAcceptanceStageProps) {
  const [agreed, setAgreed] = useState(false);

  if (missingSignup.length === 0) {
    return <p className="text-muted-foreground text-sm">Loading required documents…</p>;
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
