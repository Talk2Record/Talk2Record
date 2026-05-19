"use client";

import { Activity, AlertCircle, Loader2, WifiOff } from "lucide-react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/shared/ui/tooltip";
import { useWsConnectionStatus } from "@/shared/hooks/use-ws-bus";
import type { WsConnectionStatus } from "@/lib/ws-bus";

/**
 * Small status pill in the topbar showing whether the realtime channel
 * (notifications + record events) is connected. Drives the WS bus state into
 * a UI affordance so users notice the difference between "live updates" and
 * "polling fallback" without having to read about it.
 */
export function LiveIndicator() {
  const status = useWsConnectionStatus();
  const meta = pillFor(status);

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            aria-label={meta.aria}
            className={`hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium md:inline-flex ${meta.className}`}
          >
            <span className="relative inline-flex h-2 w-2">
              {status === "open" ? (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              ) : null}
              {meta.dot}
            </span>
            <span>{meta.label}</span>
            {status === "connecting" || status === "reconnecting" ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : null}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom">{meta.tooltip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface PillMeta {
  label: string;
  tooltip: string;
  aria: string;
  className: string;
  dot: React.ReactNode;
}

function pillFor(status: WsConnectionStatus): PillMeta {
  switch (status) {
    case "open":
      return {
        label: "Live",
        tooltip: "Realtime updates connected. New records and notifications arrive instantly.",
        aria: "Realtime updates connected",
        className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
        dot: <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />,
      };
    case "connecting":
      return {
        label: "Connecting",
        tooltip: "Establishing the realtime connection…",
        aria: "Realtime connection initialising",
        className: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        dot: <Activity className="h-2 w-2 text-amber-500" />,
      };
    case "reconnecting":
      return {
        label: "Reconnecting",
        tooltip:
          "Connection dropped — we're retrying with exponential backoff. Falling back to periodic polling in the meantime.",
        aria: "Realtime connection reconnecting",
        className: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        dot: <Activity className="h-2 w-2 text-amber-500" />,
      };
    case "failed":
      return {
        label: "Offline",
        tooltip:
          "Couldn't open a realtime connection. Data still refreshes on a slower polling cadence.",
        aria: "Realtime connection unavailable",
        className: "border-destructive/30 bg-destructive/10 text-destructive",
        dot: <AlertCircle className="h-2 w-2" />,
      };
    case "idle":
    default:
      return {
        label: "Offline",
        tooltip: "Realtime channel is idle. Reload the page if it stays this way.",
        aria: "Realtime connection idle",
        className: "border-muted bg-muted/40 text-muted-foreground",
        dot: <WifiOff className="text-muted-foreground h-2 w-2" />,
      };
  }
}
