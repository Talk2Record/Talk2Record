import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PlanCatalogItem } from "@/types/platform";

/* ---------------------------------------------------------------------------
 * Mocks
 *
 * The modal depends on:
 *   - ``useQueryClient``      → return an inert client.
 *   - ``useAuth``             → return a fake user with billing acceptance.
 *   - ``useChangePlan``       → return a stable mutation skeleton.
 *   - ``usePreferencesStore`` → resolve to a currency.
 *
 * Mocking these at the module boundary lets us assert UI strings without
 * setting up a full React Query / auth provider tree.
 * ------------------------------------------------------------------------- */

vi.mock("@tanstack/react-query", async () => {
  const actual =
    await vi.importActual<typeof import("@tanstack/react-query")>("@tanstack/react-query");
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

vi.mock("@/shared/lib/auth/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: "1",
      email: "user@example.com",
      name: "Test",
      company: "Acme",
      role: "owner",
      onboardingCompleted: true,
      legal: {
        has_required_billing_acceptance: true,
        has_required_signup_acceptance: true,
        accepted_documents: [],
        required_billing_documents: [],
        required_signup_documents: [],
      },
    },
  }),
}));

vi.mock("@/shared/hooks/use-change-plan", () => ({
  useChangePlan: () => ({ mutate: vi.fn(), isPending: false }),
  invalidateBillingQueries: vi.fn(),
  handleChangePlanSuccess: vi.fn(),
}));

vi.mock("@/store/preferences-store", () => ({
  usePreferencesStore: (selector: (_state: { currency: string }) => unknown) =>
    selector({ currency: "USD" }),
}));

import { PlanChangeModal } from "./plan-change-modal";

function makePlan(overrides: Partial<PlanCatalogItem> = {}): PlanCatalogItem {
  return {
    code: "growth",
    name: "Growth",
    currency: "USD",
    basePrice: 49,
    monthlyPrice: 49,
    region: "US",
    features: ["whatsapp_inbox", "extraction_review"],
    prices: [
      {
        interval: "month",
        amount: 49,
        currency: "USD",
        active: true,
        trialPeriod: { interval: "day", frequency: 14 },
      },
      {
        interval: "year",
        amount: 490,
        currency: "USD",
        active: true,
        trialPeriod: null,
      },
    ],
    entitlements: [],
    isHighlighted: true,
    ...overrides,
  };
}

describe("PlanChangeModal — trial + interval awareness", () => {
  it("renders the trial-aware description and CTA for a plan with a trial period", () => {
    const { getByText, getByRole } = render(
      <PlanChangeModal
        open
        plan={makePlan()}
        changeKind="new"
        interval="month"
        onOpenChange={() => {}}
      />
    );

    /* Title sources from changeKind="new" → "Subscribe to ..." */
    expect(getByText(/subscribe to growth/i)).toBeInTheDocument();
    /* Trial copy: must mention "won't be charged today" and "monthly billing". */
    expect(getByText(/won't be charged today/i)).toBeInTheDocument();
    expect(getByText(/monthly billing/i)).toBeInTheDocument();
    /* CTA text mentions "Start" + the trial label. */
    expect(getByRole("button", { name: /start.*14.*day/i })).toBeInTheDocument();
  });

  it("uses the yearly price + 'yearly billing' copy when interval='year'", () => {
    const { getByText } = render(
      <PlanChangeModal
        open
        plan={makePlan()}
        changeKind="new"
        interval="year"
        onOpenChange={() => {}}
      />
    );

    expect(getByText(/yearly price/i)).toBeInTheDocument();
    /* Yearly price must show $490 (formatted as $490 or $490.00). */
    expect(getByText(/\$490(\.00)?/)).toBeInTheDocument();
  });

  it("falls back to non-trial copy when the plan has no trial period", () => {
    const planWithoutTrial = makePlan({
      prices: [{ interval: "month", amount: 49, currency: "USD", active: true, trialPeriod: null }],
    });

    const { getByText, queryByText, getByRole } = render(
      <PlanChangeModal
        open
        plan={planWithoutTrial}
        changeKind="new"
        interval="month"
        onOpenChange={() => {}}
      />
    );

    expect(getByText(/paddle checkout will open/i)).toBeInTheDocument();
    expect(queryByText(/won't be charged today/i)).not.toBeInTheDocument();
    expect(getByRole("button", { name: /continue to checkout/i })).toBeInTheDocument();
  });

  it("uses 'Confirm plan change' CTA when changing an existing plan (not new checkout)", () => {
    const { getByRole, getByText } = render(
      <PlanChangeModal
        open
        plan={makePlan()}
        changeKind="upgrade"
        interval="month"
        onOpenChange={() => {}}
      />
    );

    expect(getByText(/upgrade to growth/i)).toBeInTheDocument();
    expect(getByRole("button", { name: /confirm plan change/i })).toBeInTheDocument();
  });
});
