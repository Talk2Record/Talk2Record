import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as { userId?: string };

  return NextResponse.json({
    user: {
      id: body.userId || `user_${Date.now()}`,
      email: "alphanganga@gmail.com",
      name: "Alpha Nganga",
      company: "Talk2Record Demo Workspace",
      role: "owner",
      onboardingCompleted: true,
    },
  });
}
