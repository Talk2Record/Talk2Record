import type { ReactNode } from "react";
import { GuestOnly } from "@/shared/components/auth-gate";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <GuestOnly>
      <div className="from-background via-background to-primary/5 flex min-h-screen items-center justify-center bg-linear-to-br px-4 py-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgb(37_99_235/0.08),transparent_36%),radial-gradient(circle_at_right,rgb(124_58_237/0.06),transparent_20%)]" />
        <div className="relative w-full">{children}</div>
      </div>
    </GuestOnly>
  );
}
