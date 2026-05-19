import type { ReactNode } from "react";

import { AuthGate } from "@/shared/components/auth-gate";

/**
 * Post-login onboarding lives outside `(auth)` because that group wraps pages
 * in `GuestOnly`, which hides children for authenticated users. LegalGate
 * sends signed-in users here when signup documents are missing.
 */
export default function OnboardingLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <div className="from-background via-background to-primary/5 flex min-h-screen items-center justify-center bg-linear-to-br px-4 py-10">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgb(37_99_235/0.08),transparent_36%),radial-gradient(circle_at_right,rgb(124_58_237/0.06),transparent_20%)]" />
        <div className="relative mx-auto flex w-full max-w-2xl justify-center">{children}</div>
      </div>
    </AuthGate>
  );
}
