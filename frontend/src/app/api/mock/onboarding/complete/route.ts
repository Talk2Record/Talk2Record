import { NextResponse } from "next/server";
import { withAcceptedDocuments } from "@/services/mock-data";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    userId?: string;
    voiceDataConsent?: boolean;
    aiReviewAcknowledged?: boolean;
    recordVerificationAcknowledged?: boolean;
  };

  if (!body.voiceDataConsent || !body.aiReviewAcknowledged || !body.recordVerificationAcknowledged) {
    return NextResponse.json(
      { message: "Review and confirm each onboarding acknowledgment before continuing." },
      { status: 400 }
    );
  }

  return NextResponse.json({
    user: {
      id: body.userId || `user_${Date.now()}`,
      email: "alphanganga@gmail.com",
      name: "Alpha Nganga",
      company: "Talk2Record Demo Workspace",
      role: "owner",
      onboardingCompleted: true,
      legal: withAcceptedDocuments(["terms-of-service", "privacy-policy"]),
    },
  });
}
