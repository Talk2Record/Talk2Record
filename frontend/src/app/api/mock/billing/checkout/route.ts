import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as { plan?: string; acceptedBillingTerms?: boolean };

  if (!body.acceptedBillingTerms) {
    return NextResponse.json(
      { message: "Accept the billing policy and auto-renewal terms before checkout." },
      { status: 400 }
    );
  }

  return NextResponse.json({
    status: `Checkout started for ${body.plan || "selected"} plan.`,
    checkoutUrl: "/dashboard/billing?checkout=mocked",
  });
}
