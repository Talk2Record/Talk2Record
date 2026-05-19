"use client";

import { useEffect, useState } from "react";
import { ShieldAlert, X } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { useImpersonationSession } from "@/shared/hooks/use-impersonation";

/**
 * Persistent banner shown across the top of the dashboard while an operator
 * is impersonating another user. Renders a live countdown (the backend
 * issues a 15-minute access token), an "Exit" button that restores the
 * original session, and auto-exits when the timer hits zero.
 */
export function ImpersonationBanner() {
  const { active, stopImpersonation } = useImpersonationSession();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [active]);

  useEffect(() => {
    if (!active) return;
    if (now < active.expiresAt) return;
    void stopImpersonation({ reason: "expired" });
  }, [active, now, stopImpersonation]);

  if (!active) return null;

  const remainingMs = Math.max(0, active.expiresAt - now);
  const minutes = Math.floor(remainingMs / 60_000);
  const seconds = Math.floor((remainingMs % 60_000) / 1000)
    .toString()
    .padStart(2, "0");

  return (
    <div className="border-b border-amber-500/30 bg-amber-500/15 px-4 py-2 text-amber-800 md:px-8 dark:text-amber-200">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <ShieldAlert className="h-4 w-4 shrink-0" />
        <span className="font-medium">
          Impersonating <span className="font-mono">{active.targetEmail}</span> · session ends in{" "}
          {minutes}:{seconds}
        </span>
        <Button
          size="sm"
          variant="outline"
          className="ml-auto rounded-xl border-amber-500/40 bg-transparent text-amber-900 dark:text-amber-100"
          onClick={() => void stopImpersonation({ reason: "manual" })}
        >
          <X className="mr-1 h-3.5 w-3.5" />
          End impersonation
        </Button>
      </div>
    </div>
  );
}
