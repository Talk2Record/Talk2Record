"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SegmentError error={error} reset={reset} title="This page crashed" segmentLabel="dashboard" />
  );
}
