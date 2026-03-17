import { NextResponse } from "next/server";
import { integrations } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(integrations);
}
