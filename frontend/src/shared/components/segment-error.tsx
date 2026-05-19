"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCcw } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

interface SegmentErrorProps {
  /** Error from Next's segment error boundary. */
  error: Error & { digest?: string };
  /** Re-render the segment with a fresh request. */
  reset: () => void;
  /** Headline shown in the card; defaults to a generic message. */
  title?: string;
  /** Sub-headline shown below the title; defaults to error.message. */
  description?: string;
  /** Optional link to navigate away from the failing segment. */
  backHref?: string;
  /** Label for the back link. */
  backLabel?: string;
  /** Tag printed inline next to "Reference" — handy when triaging shared segments. */
  segmentLabel?: string;
}

/**
 * Shared layout for per-segment error.tsx pages. Centralising the look keeps
 * Cards, buttons, and tone consistent without each segment re-implementing
 * the same retry / back / digest plumbing.
 */
export function SegmentError({
  error,
  reset,
  title = "Something went wrong here",
  description,
  backHref = "/dashboard",
  backLabel = "Back to dashboard",
  segmentLabel,
}: SegmentErrorProps) {
  useEffect(() => {
    console.error(`[${segmentLabel ?? "segment"} error boundary]`, error);
  }, [error, segmentLabel]);

  const resolvedDescription =
    description ||
    error.message ||
    "We hit an unexpected error rendering this page. Try again or head back to the dashboard.";

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4 px-4 py-12">
      <Card className="border-destructive/30">
        <CardHeader className="flex flex-row items-start gap-3">
          <span className="bg-destructive/10 text-destructive inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div className="space-y-1">
            <CardTitle>{title}</CardTitle>
            <CardDescription>{resolvedDescription}</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error.digest ? (
            <p className="text-muted-foreground text-xs">
              Reference:{" "}
              <code className="bg-muted rounded px-1.5 py-0.5 font-mono text-[11px]">
                {error.digest}
              </code>
              {segmentLabel ? <span className="ml-2 opacity-70">({segmentLabel})</span> : null}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={reset} className="gap-2">
              <RefreshCcw className="h-4 w-4" />
              Try again
            </Button>
            <Button asChild variant="outline">
              <Link href={backHref}>{backLabel}</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
