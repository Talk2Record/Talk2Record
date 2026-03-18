import { NextResponse } from "next/server";
import { withAcceptedDocuments } from "@/services/mock-data";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    name?: string;
    company?: string;
    email?: string;
    password?: string;
    acceptedDocumentKeys?: string[];
  };

  if (!body.name || !body.company || !body.email || !body.password) {
    return NextResponse.json({ message: "All fields are required." }, { status: 400 });
  }

  const requiredDocumentKeys = ["terms-of-service", "privacy-policy"];
  const acceptedDocumentKeys = body.acceptedDocumentKeys || [];
  const hasRequiredSignupAcceptance = requiredDocumentKeys.every((documentKey) =>
    acceptedDocumentKeys.includes(documentKey)
  );

  if (!hasRequiredSignupAcceptance) {
    return NextResponse.json(
      { message: "Accept the Terms of Service and Privacy Policy to create an account." },
      { status: 400 }
    );
  }

  return NextResponse.json({
    user: {
      id: `user_${Date.now()}`,
      email: body.email,
      name: body.name,
      company: body.company,
      role: "owner",
      onboardingCompleted: false,
      legal: withAcceptedDocuments(acceptedDocumentKeys),
    },
  });
}
