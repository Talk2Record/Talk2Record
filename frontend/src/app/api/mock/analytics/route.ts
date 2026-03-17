import { NextResponse } from "next/server";
import { analyticsSnapshot } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(analyticsSnapshot);
}
