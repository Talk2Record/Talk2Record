import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    name?: string;
    company?: string;
    email?: string;
    password?: string;
  };

  if (!body.name || !body.company || !body.email || !body.password) {
    return NextResponse.json({ message: "All fields are required." }, { status: 400 });
  }

  return NextResponse.json({
    user: {
      id: `user_${Date.now()}`,
      email: body.email,
      name: body.name,
      company: body.company,
      role: "owner",
      onboardingCompleted: false,
    },
  });
}
