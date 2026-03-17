import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="from-background to-muted/40 flex min-h-screen items-center justify-center bg-linear-to-br px-4 py-10">
      {children}
    </div>
  );
}
