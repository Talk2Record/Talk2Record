"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function SettingsError({
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
      title="Settings failed to load"
      description="Your account preferences couldn't be rendered. Reload the section or head back to the dashboard."
      backHref="/dashboard"
      backLabel="Back to dashboard"
      segmentLabel="settings"
    />
  );
}
