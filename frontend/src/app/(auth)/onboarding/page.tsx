"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuth } from "@/shared/lib/auth/auth-context";
import { onboardingService } from "@/services/platform-service";
import { trackEvent } from "@/lib/analytics";
import { getHeatmapAdapter } from "@/lib/heatmap";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export default function OnboardingPage() {
  const router = useRouter();
  const heatmap = getHeatmapAdapter();
  const { completeOnboarding, isLoading } = useAuth();
  const [voiceDataConsent, setVoiceDataConsent] = useState(false);
  const [aiReviewAcknowledged, setAiReviewAcknowledged] = useState(false);
  const [recordVerificationAcknowledged, setRecordVerificationAcknowledged] = useState(false);
  const [error, setError] = useState("");
  const { data: steps = [] } = useQuery({
    queryKey: ["onboarding-steps"],
    queryFn: onboardingService.getSteps,
  });

  async function finishOnboarding() {
    if (!voiceDataConsent || !aiReviewAcknowledged || !recordVerificationAcknowledged) {
      setError("Review and confirm each legal acknowledgement before continuing.");
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
      router.push("/dashboard");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Unable to complete onboarding.");
    }
  }

  return (
    <Card className="w-full max-w-2xl border-primary/10 shadow-(--shadow-lg)">
      <CardHeader>
        <div className="bg-primary/10 text-primary inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium">
          Guided setup
        </div>
        <CardTitle>Finish onboarding</CardTitle>
        <CardDescription>
          Connect WhatsApp, validate your first note, and confirm the defaults that keep your workspace reliable.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-2xl border border-primary/10 bg-background/80 p-4">
          <p className="text-sm font-medium">Before you continue</p>
          <div className="mt-3 space-y-3 text-sm text-muted-foreground">
            <label className="flex items-start gap-3">
              <input
                checked={voiceDataConsent}
                className="mt-1 h-4 w-4 rounded border-primary/20"
                onChange={(event) => setVoiceDataConsent(event.target.checked)}
                type="checkbox"
              />
              <span>You confirm you have consent to process voice data.</span>
            </label>
            <label className="flex items-start gap-3">
              <input
                checked={aiReviewAcknowledged}
                className="mt-1 h-4 w-4 rounded border-primary/20"
                onChange={(event) => setAiReviewAcknowledged(event.target.checked)}
                type="checkbox"
              />
              <span>You understand AI outputs may not be 100% accurate.</span>
            </label>
            <label className="flex items-start gap-3">
              <input
                checked={recordVerificationAcknowledged}
                className="mt-1 h-4 w-4 rounded border-primary/20"
                onChange={(event) => setRecordVerificationAcknowledged(event.target.checked)}
                type="checkbox"
              />
              <span>You are responsible for verifying records before operational use.</span>
            </label>
          </div>
        </div>
        {steps.map((step, index) => (
          <div key={step.id} className="rounded-2xl border border-primary/10 bg-background/80 p-4">
            <div className="flex items-start gap-3">
              <div className="bg-primary/10 text-primary flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold">
                {index + 1}
              </div>
              <div>
                <p className="text-sm font-medium">{step.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Status: {step.completed ? "Complete" : "Pending"}
                </p>
              </div>
            </div>
          </div>
        ))}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button className="w-full rounded-xl" disabled={isLoading} onClick={() => finishOnboarding()}>
          I understand and continue
        </Button>
      </CardContent>
    </Card>
  );
}
