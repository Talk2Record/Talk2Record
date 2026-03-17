import { NextResponse } from "next/server";
import { settingsProfile } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(settingsProfile);
}
