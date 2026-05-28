"use client";

import { Suspense, useEffect, useState } from "react";

import { Loader2 } from "lucide-react";
import { openPaddleCheckout } from "@/shared/hooks/use-paddle-checkout";
import { useSearchParams } from "next/navigation";

function CheckoutLauncher() {
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const transactionId = searchParams.get("_ptxn");
    if (!transactionId) {
      setError("Missing checkout transaction.");
      return;
    }

    void openPaddleCheckout({ transactionId }).then((opened) => {
      if (!opened) {
        setError("Could not open Paddle checkout.");
      }
    });
  }, [searchParams]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="text-lg font-medium">Checkout unavailable</p>
        <p className="text-muted-foreground text-sm">{error}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center gap-3 px-6 text-center">
      <Loader2 className="text-primary h-8 w-8 animate-spin" />
      <p className="text-muted-foreground text-sm">Opening secure checkout…</p>
    </main>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center px-6">
          <Loader2 className="text-primary h-8 w-8 animate-spin" />
        </main>
      }
    >
      <CheckoutLauncher />
    </Suspense>
  );
}
