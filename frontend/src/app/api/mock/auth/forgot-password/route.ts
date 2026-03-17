import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as { email?: string };

  return NextResponse.json({
    status: `Password reset link queued for ${body.email || "your email"}.`,
  });
}
