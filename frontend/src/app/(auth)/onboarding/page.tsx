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
        <Button className="w-full rounded-xl" disabled={isLoading} onClick={() => finishOnboarding()}>
          Enter dashboard
        </Button>
      </CardContent>
    </Card>
  );
}
