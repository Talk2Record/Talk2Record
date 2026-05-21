import { act, render } from "@testing-library/react";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { SubscriptionBanner } from "./subscription-banner";
import { TrialBanner } from "./trial-banner";

/**
 * Pin Date.now so "days left" copy is deterministic. Without this the
 * countdown drifts every wall-clock day and these tests would be flaky in
 * CI.
 */
const FIXED_NOW = new Date("2026-05-21T12:00:00Z").getTime();

beforeAll(() => {
  vi.spyOn(Date, "now").mockReturnValue(FIXED_NOW);
});
afterAll(() => {
  vi.restoreAllMocks();
});

describe("TrialBanner", () => {
  it("renders the countdown, the 'not charged yet' copy and the conversion price", () => {
    /* Trial ends 9 days after FIXED_NOW (Jun 1 → Sep would be too far). */
    const { getByText, getByRole } = render(
      <TrialBanner trialEndsAt="2026-05-30T00:00:00Z" amount={49} currency="USD" interval="month" />
    );

    expect(getByText(/trial ends in 9 days/i)).toBeInTheDocument();
    expect(getByText(/haven't been charged yet/i)).toBeInTheDocument();
    /* Conversion price ought to render as "$49.00/mo" (or locale variant). */
    expect(getByText(/\$49(\.00)?\/mo/)).toBeInTheDocument();
    expect(getByRole("status")).toHaveAttribute("aria-label", "Trial ends May 30, 2026");
  });

  it("uses /yr suffix when interval is 'year'", () => {
    const { getByText } = render(
      <TrialBanner trialEndsAt="2026-05-30T00:00:00Z" amount={490} currency="USD" interval="year" />
    );
    expect(getByText(/\$490(\.00)?\/yr/)).toBeInTheDocument();
  });

  it("renders a 'Manage billing' CTA when onManageBilling is provided", () => {
    const onManageBilling = vi.fn();
    const { getByRole } = render(
      <TrialBanner
        trialEndsAt="2026-05-30T00:00:00Z"
        amount={49}
        currency="USD"
        onManageBilling={onManageBilling}
      />
    );
    const cta = getByRole("button", { name: /manage billing/i });
    act(() => {
      (cta as HTMLButtonElement).click();
    });
    expect(onManageBilling).toHaveBeenCalledTimes(1);
  });

  it("falls back to generic copy when no price is supplied", () => {
    const { getByText } = render(<TrialBanner trialEndsAt="2026-05-30T00:00:00Z" />);
    expect(getByText(/card on file will be charged/i)).toBeInTheDocument();
  });
});

describe("SubscriptionBanner — trialing delegation", () => {
  it("delegates trialing status to TrialBanner using trialEndsAt when present", () => {
    const { getByText, queryByText } = render(
      <SubscriptionBanner
        status="trialing"
        periodEnd={null}
        trialEndsAt="2026-05-30T00:00:00Z"
        amount={49}
        currency="USD"
        interval="month"
      />
    );
    /* TrialBanner-specific copy must appear; the generic "Upgrade" CTA of
       the legacy spec must NOT. */
    expect(getByText(/haven't been charged yet/i)).toBeInTheDocument();
    expect(queryByText(/^Upgrade$/)).not.toBeInTheDocument();
  });

  it("falls back to periodEnd when trialEndsAt is not provided", () => {
    const { getByText } = render(
      <SubscriptionBanner
        status="trialing"
        periodEnd="2026-05-30T00:00:00Z"
        amount={49}
        currency="USD"
        interval="month"
      />
    );
    expect(getByText(/trial ends in 9 days/i)).toBeInTheDocument();
  });

  it("renders nothing for trialing with no end date", () => {
    const { container } = render(
      <SubscriptionBanner status="trialing" periodEnd={null} trialEndsAt={null} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the generic past_due banner for non-trialing statuses", () => {
    const onCta = vi.fn();
    const { getByText, getByRole } = render(<SubscriptionBanner status="past_due" onCta={onCta} />);
    expect(getByText(/payment failed/i)).toBeInTheDocument();
    const cta = getByRole("button", { name: /update payment/i });
    act(() => {
      (cta as HTMLButtonElement).click();
    });
    expect(onCta).toHaveBeenCalledTimes(1);
  });
});
