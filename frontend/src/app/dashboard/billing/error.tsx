"use client";

import { SegmentError } from "@/shared/components/segment-error";

export default function BillingError({
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
      title="Billing didn't load"
      description="Your subscription and invoices couldn't be rendered. Your billing status is unaffected — try again in a moment."
      backHref="/dashboard"
      backLabel="Back to dashboard"
      segmentLabel="billing"
    />
  );
}
