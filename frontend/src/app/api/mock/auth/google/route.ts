import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json({
    user: {
      id: "google_mock_user",
      email: "alphanganga@gmail.com",
      name: "Alpha Nganga",
      company: "Talk2Record Demo Workspace",
      role: "owner",
      onboardingCompleted: true,
    },
  });
}
