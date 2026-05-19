"use client";

import type React from "react";
import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCcw } from "lucide-react";

const GlobalError = ({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) => {
  useEffect(() => {
    console.error("[global error boundary]", error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div className="bg-background flex min-h-screen items-center justify-center px-4">
          <div className="border-destructive/30 bg-card w-full max-w-md space-y-5 rounded-2xl border p-8 text-center shadow-sm">
            <div className="bg-destructive/10 text-destructive mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold">Something went wrong</h1>
              <p className="text-muted-foreground text-sm">
                An unexpected error occurred. You can try again or head back to the dashboard.
              </p>
            </div>
            {error?.digest ? (
              <p className="text-muted-foreground text-xs">
                Reference: <code className="bg-muted rounded px-1 py-0.5">{error.digest}</code>
              </p>
            ) : null}
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => reset()}
                className="bg-primary text-primary-foreground inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium"
              >
                <RefreshCcw className="h-4 w-4" />
                Try again
              </button>
              <Link
                href="/"
                className="text-foreground rounded-md border px-4 py-2 text-sm font-medium"
              >
                Back to home
              </Link>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
};

export default GlobalError;
