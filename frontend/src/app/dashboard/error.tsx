"use client";

import { useEffect } from "react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[dashboard error boundary]", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-xl px-4 py-12">
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle>This page crashed</CardTitle>
          <CardDescription>{error.message || "An unexpected error occurred."}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {error.digest ? (
            <p className="text-muted-foreground text-xs">
              Reference: <code>{error.digest}</code>
            </p>
          ) : null}
          <div className="flex items-center gap-3">
            <Button onClick={reset}>Try again</Button>
            <Button variant="outline" onClick={() => (window.location.href = "/dashboard")}>
              Back to dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
