"use client";

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
  const { data: steps = [] } = useQuery({
    queryKey: ["onboarding-steps"],
    queryFn: onboardingService.getSteps,
  });

  async function finishOnboarding() {
    heatmap.identifyStep("company-setup");
    trackEvent("onboarding_step_completed", { step: "company-setup" });
    await completeOnboarding();
    router.push("/dashboard");
  }

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Finish onboarding</CardTitle>
        <CardDescription>Connect WhatsApp, validate a note, and confirm workspace defaults.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {steps.map((step, index) => (
          <div key={step.id} className="rounded-xl border p-4">
            <p className="text-sm font-medium">
              {index + 1}. {step.title}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Status: {step.completed ? "Complete" : "Pending"}
            </p>
          </div>
        ))}
        <Button className="w-full" disabled={isLoading} onClick={() => finishOnboarding()}>
          Enter dashboard
        </Button>
      </CardContent>
    </Card>
  );
}
