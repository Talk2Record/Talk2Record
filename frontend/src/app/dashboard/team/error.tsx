"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function TeamError({
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
      title="Team view crashed"
      description="The team list couldn't be rendered. Try again or return to the dashboard while we look into it."
      backHref="/dashboard"
      backLabel="Back to dashboard"
      segmentLabel="team"
    />
  );
}
