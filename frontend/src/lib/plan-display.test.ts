import { describe, expect, it } from "vitest";

import {
  annualSavingsPercent,
  formatPlanPriceForInterval,
  formatPlanTrialLabel,
} from "./plan-display";
import type { PlanCatalogItem } from "@/types/platform";

/**
 * Factory for a minimal ``PlanCatalogItem`` with active monthly + annual
 * prices. Keeps each test focused on the behavior under test.
 */
function makePlan(overrides: Partial<PlanCatalogItem> = {}): PlanCatalogItem {
  return {
    code: "growth",
    name: "Growth",
    currency: "USD",
    basePrice: 49,
    monthlyPrice: 49,
    region: "US",
    features: [],
    prices: [
      { interval: "month", amount: 49, currency: "USD", active: true, trialPeriod: null },
      { interval: "year", amount: 470, currency: "USD", active: true, trialPeriod: null },
    ],
    entitlements: [],
    isHighlighted: false,
    ...overrides,
  };
}

describe("formatPlanPriceForInterval", () => {
  it("formats monthly price as $X /mo", () => {
    expect(formatPlanPriceForInterval(makePlan(), "month")).toContain("/mo");
    expect(formatPlanPriceForInterval(makePlan(), "month")).toContain("49");
  });

  it("formats yearly price with monthly-equivalent in parentheses", () => {
    const out = formatPlanPriceForInterval(makePlan(), "year");
    expect(out).toContain("/yr");
    expect(out).toContain("470");
    // 470 / 12 ≈ 39.17 — the monthly-equivalent should be in the output.
    expect(out).toMatch(/39\.\d{2}/);
  });

  it("falls back to 12× monthlyPrice when no annual price is published", () => {
    const plan = makePlan({
      prices: [{ interval: "month", amount: 49, currency: "USD", active: true, trialPeriod: null }],
    });
    const out = formatPlanPriceForInterval(plan, "year");
    expect(out).toContain("588"); // 49 × 12
  });
});

describe("annualSavingsPercent", () => {
  it("returns the saving percent when annual is cheaper than 12× monthly", () => {
    // 49 × 12 = 588, annual = 470 → saved 118 → 20%.
    expect(annualSavingsPercent(makePlan())).toBe(20);
  });

  it("returns 0 when annual is not cheaper than 12× monthly", () => {
    const plan = makePlan({
      prices: [
        { interval: "month", amount: 49, currency: "USD", active: true, trialPeriod: null },
        { interval: "year", amount: 588, currency: "USD", active: true, trialPeriod: null },
      ],
    });
    expect(annualSavingsPercent(plan)).toBe(0);
  });

  it("returns 0 when one of the prices is missing", () => {
    const plan = makePlan({
      prices: [{ interval: "month", amount: 49, currency: "USD", active: true, trialPeriod: null }],
    });
    expect(annualSavingsPercent(plan)).toBe(0);
  });
});

describe("formatPlanTrialLabel", () => {
  it("returns the monthly trial label by default", () => {
    const plan = makePlan({
      prices: [
        {
          interval: "month",
          amount: 49,
          currency: "USD",
          active: true,
          trialPeriod: { interval: "day", frequency: 14 },
        },
        { interval: "year", amount: 470, currency: "USD", active: true, trialPeriod: null },
      ],
    });
    expect(formatPlanTrialLabel(plan)).toBe("14-days free trial");
  });

  it("picks the trial off the requested interval", () => {
    const plan = makePlan({
      prices: [
        { interval: "month", amount: 49, currency: "USD", active: true, trialPeriod: null },
        {
          interval: "year",
          amount: 470,
          currency: "USD",
          active: true,
          trialPeriod: { interval: "day", frequency: 30 },
        },
      ],
    });
    expect(formatPlanTrialLabel(plan, "year")).toBe("30-days free trial");
    expect(formatPlanTrialLabel(plan, "month")).toBeNull();
  });

  it("returns null when no trial is configured for the interval", () => {
    expect(formatPlanTrialLabel(makePlan(), "month")).toBeNull();
  });
});
