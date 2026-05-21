import { describe, expect, it } from "vitest";

import { mapBillingSnapshot } from "./platform-mappers";
import type { BillingSnapshot, SubscriptionSnapshot } from "@/types/platform";

function makeBillingSnapshot(
  overrides: Partial<SubscriptionSnapshot> = {},
  invoices: BillingSnapshot["invoices"] = []
): BillingSnapshot {
  const sub: SubscriptionSnapshot = {
    plan: "Growth",
    planCode: "growth",
    amount: 49,
    currency: "USD",
    seats: 1,
    voiceNotesProcessed: 12,
    includedVoiceNotes: 500,
    renewalDate: "2026-06-01T00:00:00Z",
    billingInterval: "month",
    trialEndsAt: null,
    status: "active",
    usage: {
      featureKey: "ai.usage",
      used: 12,
      included: 500,
      percentUsed: 2,
      periodStart: "2026-05-01T00:00:00Z",
      periodEnd: "2026-06-01T00:00:00Z",
    },
    ...overrides,
  };
  return { subscription: sub, invoices };
}

describe("mapBillingSnapshot", () => {
  it("preserves Phase 6 fields (billingInterval, trialEndsAt, status, usage)", () => {
    const snapshot = makeBillingSnapshot({
      billingInterval: "year",
      trialEndsAt: "2026-05-30T00:00:00Z",
      status: "trialing",
    });
    const mapped = mapBillingSnapshot(snapshot);

    expect(mapped.subscription.billingInterval).toBe("year");
    expect(mapped.subscription.trialEndsAt).toBe("2026-05-30T00:00:00Z");
    expect(mapped.subscription.status).toBe("trialing");
    expect(mapped.subscription.usage.featureKey).toBe("ai.usage");
    expect(mapped.subscription.usage.used).toBe(12);
    expect(mapped.subscription.usage.included).toBe(500);
    expect(mapped.subscription.usage.percentUsed).toBe(2);
  });

  it("coerces numeric usage fields from string payloads", () => {
    /* Some legacy/mocked endpoints stringify integers; the mapper should
       hand the frontend numbers so totals + arithmetic work. */
    const snapshot = makeBillingSnapshot({
      usage: {
        featureKey: "ai.usage",
        used: "30" as unknown as number,
        included: "1000" as unknown as number,
        percentUsed: "3" as unknown as number,
        periodStart: "2026-05-01T00:00:00Z",
        periodEnd: "2026-06-01T00:00:00Z",
      },
    });
    const mapped = mapBillingSnapshot(snapshot);

    expect(mapped.subscription.usage.used).toBe(30);
    expect(typeof mapped.subscription.usage.used).toBe("number");
    expect(mapped.subscription.usage.included).toBe(1000);
    expect(mapped.subscription.usage.percentUsed).toBe(3);
  });

  it("falls back to legacy voiceNotes counters when ``usage`` is missing", () => {
    /* Until every server has Phase 2 deployed the mapper has to tolerate a
       legacy payload that omits the ``usage`` block. We synthesize one
       from ``voiceNotesProcessed`` / ``includedVoiceNotes`` so the
       dashboard never blows up on `undefined.percentUsed`. */
    const snapshot = makeBillingSnapshot();
    /* Strip the new field to simulate a pre-Phase-2 payload. */
    const legacyPayload = {
      ...snapshot,
      subscription: {
        ...snapshot.subscription,
        usage: undefined as unknown as SubscriptionSnapshot["usage"],
        voiceNotesProcessed: 9,
        includedVoiceNotes: 100,
      },
    };
    const mapped = mapBillingSnapshot(legacyPayload as BillingSnapshot);

    expect(mapped.subscription.usage.featureKey).toBe("ai.usage");
    expect(mapped.subscription.usage.used).toBe(9);
    expect(mapped.subscription.usage.included).toBe(100);
    expect(mapped.subscription.usage.percentUsed).toBe(0);
  });

  it("defaults billingInterval to 'month' and status/trialEndsAt to null for legacy payloads", () => {
    const snapshot = makeBillingSnapshot();
    /* Pretend the backend hasn't been upgraded yet — strip the Phase 6
       fields. The mapper must restore safe defaults. */
    const legacyPayload = {
      ...snapshot,
      subscription: {
        ...snapshot.subscription,
        billingInterval: undefined as unknown as SubscriptionSnapshot["billingInterval"],
        trialEndsAt: undefined as unknown as SubscriptionSnapshot["trialEndsAt"],
        status: undefined as unknown as SubscriptionSnapshot["status"],
      },
    };
    const mapped = mapBillingSnapshot(legacyPayload as BillingSnapshot);

    expect(mapped.subscription.billingInterval).toBe("month");
    expect(mapped.subscription.trialEndsAt).toBeNull();
    expect(mapped.subscription.status).toBeNull();
  });
});
