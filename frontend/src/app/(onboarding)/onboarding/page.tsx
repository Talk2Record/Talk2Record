import { Suspense } from "react";

import { Skeleton } from "@/shared/ui/skeleton";
import { OnboardingPageContent } from "@/app/(onboarding)/onboarding/onboarding-content";

export default function OnboardingPage() {
  return (
    <Suspense fallback={<OnboardingPageFallback />}>
      <OnboardingPageContent />
    </Suspense>
  );
}

function OnboardingPageFallback() {
  return (
    <div className="border-primary/10 w-full max-w-2xl space-y-4 rounded-2xl border p-8">
      <Skeleton className="h-5 w-1/3" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-32 w-full" />
    </div>
  );
}
