import { describe, expect, it } from "vitest";
import { POST as checkoutPost } from "./billing/checkout/route";
import { POST as registerPost } from "./auth/register/route";
import { POST as integrationTestPost } from "./integrations/test/route";
import { POST as onboardingCompletePost } from "./onboarding/complete/route";

describe("mock legal flow enforcement", () => {
  it("requires signup acceptance for register", async () => {
    const response = await registerPost(
      new Request("http://localhost/api/mock/auth/register", {
        method: "POST",
        body: JSON.stringify({
          name: "Owner",
          company: "Acme",
          email: "owner@example.com",
          password: "password123",
          acceptedDocumentKeys: ["terms-of-service"],
        }),
      })
    );

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toMatchObject({
      message: expect.stringMatching(/terms of service and privacy policy/i),
    });
  });

  it("requires onboarding acknowledgements", async () => {
    const response = await onboardingCompletePost(
      new Request("http://localhost/api/mock/onboarding/complete", {
        method: "POST",
        body: JSON.stringify({
          userId: "user_1",
          voiceDataConsent: true,
          aiReviewAcknowledged: false,
          recordVerificationAcknowledged: true,
        }),
      })
    );

    expect(response.status).toBe(400);
  });

  it("requires billing acceptance before checkout", async () => {
    const response = await checkoutPost(
      new Request("http://localhost/api/mock/billing/checkout", {
        method: "POST",
        body: JSON.stringify({
          plan: "Growth",
          acceptedBillingTerms: false,
        }),
      })
    );

    expect(response.status).toBe(400);
  });

  it("requires permission confirmation before integration tests", async () => {
    const response = await integrationTestPost(
      new Request("http://localhost/api/mock/integrations/test", {
        method: "POST",
        body: JSON.stringify({
          id: "whatsapp",
          confirmedPermission: false,
        }),
      })
    );

    expect(response.status).toBe(400);
  });
});
