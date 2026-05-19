"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function AdminError({
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
      title="Platform admin view crashed"
      description="The admin tools failed to render. Try again or head back to the dashboard."
      backHref="/dashboard"
      backLabel="Back to dashboard"
      segmentLabel="admin"
    />
  );
}
