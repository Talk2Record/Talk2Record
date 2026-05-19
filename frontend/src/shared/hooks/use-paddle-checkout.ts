"use client";

import { getPaddle } from "@/shared/lib/paddle";
import { notifyApiError } from "@/shared/lib/notify-api-error";

interface OpenPaddleCheckoutOptions {
  transactionId: string;
  successUrl?: string;
}

export async function openPaddleCheckout({
  transactionId,
  successUrl,
}: OpenPaddleCheckoutOptions): Promise<boolean> {
  try {
    const paddle = await getPaddle();
    if (!paddle) {
      throw new Error("Paddle.js failed to initialize.");
    }

    paddle.Checkout.open({
      transactionId,
      settings: {
        displayMode: "overlay",
        successUrl,
      },
    });
    return true;
  } catch (error) {
    notifyApiError(error, { title: "Could not open checkout" });
    return false;
  }
}
