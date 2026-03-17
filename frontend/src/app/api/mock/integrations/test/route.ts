import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as { secret?: string };

  return NextResponse.json({
    status: "Connection looks healthy.",
    maskedSecret: body.secret ? `${body.secret.slice(0, 4)}***${body.secret.slice(-2)}` : undefined,
  });
}
