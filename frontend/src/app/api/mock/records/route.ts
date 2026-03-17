import { NextResponse } from "next/server";
import { records } from "@/services/mock-data";

export async function GET() {
  return NextResponse.json(records);
}
