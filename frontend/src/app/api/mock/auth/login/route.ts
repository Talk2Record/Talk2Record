import { NextResponse } from "next/server";
import { defaultLegalStatus } from "@/services/mock-data";

export async function POST(request: Request) {
  const body = (await request.json()) as { email?: string; password?: string };

  if (!body.email || !body.password || body.password.length < 6) {
    return NextResponse.json({ message: "Enter a valid email and password." }, { status: 400 });
  }

  return NextResponse.json({
    user: {
      id: `user_${Date.now()}`,
      email: body.email,
      name: body.email.split("@")[0].replace(/[._-]/g, " "),
      company: "Talk2Record Demo Workspace",
      role: "owner",
      onboardingCompleted: false,
      legal: defaultLegalStatus,
    },
  });
}
