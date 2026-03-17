import { NextResponse } from "next/server";
import { onboardingSteps } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(onboardingSteps);
}
