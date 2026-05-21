"use client";

import { useCallback, useSyncExternalStore } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, Rocket, X } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { useOnboardingSnapshot } from "@/shared/hooks/use-onboarding";

const DISMISS_KEY = "talk2record:onboarding-card:dismissed-session";

function subscribeToStorage(callback: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const handler = (event: StorageEvent) => {
    if (event.key === DISMISS_KEY) callback();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function readDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

function readDismissedServer(): boolean {
  return false;
}

const stepHref: Record<string, string> = {
  "company-setup": "/onboarding",
  "choose-plan": "/onboarding",
  "connect-whatsapp": "/dashboard/integrations",
  "first-voice-note": "/dashboard/records",
};

export function OnboardingCard() {
  const snapshot = useOnboardingSnapshot();
  const dismissed = useSyncExternalStore(subscribeToStorage, readDismissed, readDismissedServer);

  const dismiss = useCallback(() => {
    if (typeof window === "undefined") return;
    try {
      window.sessionStorage.setItem(DISMISS_KEY, "1");
      window.dispatchEvent(new StorageEvent("storage", { key: DISMISS_KEY, newValue: "1" }));
    } catch {
      // Ignore — at worst the dismissal doesn't survive a refresh.
    }
  }, []);

  if (snapshot.isLoading) return null;
  if (snapshot.status === "complete") return null;
  if (dismissed && snapshot.status !== "ready-to-finalize") return null;

  const completed = snapshot.steps.filter((s) => s.completed).length;
  const total = snapshot.steps.length;
  const requiredCompleted = snapshot.steps.filter((s) => s.required && s.completed).length;
  const requiredTotal = snapshot.steps.filter((s) => s.required).length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const canDismiss = snapshot.requiredStepsComplete;

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div>
          <div className="bg-primary/10 text-primary inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-xs font-medium">
            <Rocket className="h-3.5 w-3.5" />
            Finish setting up
          </div>
          <CardTitle className="mt-2 text-lg">
            {snapshot.status === "ready-to-finalize"
              ? "You're ready to finalize onboarding"
              : "Welcome — complete required setup steps"}
          </CardTitle>
          <CardDescription>
            {snapshot.status === "ready-to-finalize"
              ? "Company profile and plan are set. Confirm the legal acknowledgements to wrap up."
              : `${requiredCompleted} of ${requiredTotal} required steps done (${completed}/${total} total, ${percent}%).`}
          </CardDescription>
        </div>
        {canDismiss && snapshot.status !== "ready-to-finalize" ? (
          <button
            type="button"
            onClick={dismiss}
            aria-label="Dismiss until next session"
            className="text-muted-foreground hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-full"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3">
        {snapshot.status === "ready-to-finalize" ? (
          <Button asChild className="rounded-xl">
            <Link href="/onboarding">Open finalisation flow</Link>
          </Button>
        ) : (
          <ul className="space-y-2">
            {snapshot.steps.map((step) => {
              const href = stepHref[step.id];
              return (
                <li
                  key={step.id}
                  className="border-primary/10 bg-background/70 flex items-center justify-between gap-3 rounded-xl border p-3"
                >
                  <div className="flex items-start gap-3">
                    {step.completed ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                    ) : (
                      <Circle className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
                    )}
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium">{step.title}</p>
                        {step.required ? (
                          <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium tracking-wide text-amber-800 uppercase dark:text-amber-200">
                            Required
                          </span>
                        ) : null}
                      </div>
                      <p className="text-muted-foreground text-xs">{step.description}</p>
                    </div>
                  </div>
                  {href && !step.completed ? (
                    <Button asChild size="sm" variant="outline" className="rounded-xl">
                      <Link href={href}>Start</Link>
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
