import { NextResponse } from "next/server";
import { billingSnapshot } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(billingSnapshot);
}
