"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function AuthError({
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
      title="We couldn't render this page"
      description="Sign-in flow failed to render. Try again or return to the start."
      backHref="/login"
      backLabel="Back to sign in"
      segmentLabel="auth"
    />
  );
}
