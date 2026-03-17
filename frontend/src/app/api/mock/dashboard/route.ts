import { NextResponse } from "next/server";
import { dashboardOverview } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(dashboardOverview);
}
