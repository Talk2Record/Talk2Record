"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function RecordsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <SegmentError
      error={error}
      reset={reset}
      title="We couldn't load your records"
      description="The records list failed to render. This is usually a transient network or backend hiccup."
      backHref="/dashboard"
      backLabel="Back to dashboard"
      segmentLabel="records"
    />
  );
}
