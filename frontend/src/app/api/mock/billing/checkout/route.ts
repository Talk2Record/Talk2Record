import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as { plan?: string };

  return NextResponse.json({
    status: `Checkout started for ${body.plan || "selected"} plan.`,
    checkoutUrl: "/dashboard/billing?checkout=mocked",
  });
}
