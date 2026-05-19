import { initializePaddle, type Paddle } from "@paddle/paddle-js";

import { api } from "@/lib/api";

interface PaddleConfigResponse {
  clientSideToken: string;
  environment: "sandbox" | "production";
}

let paddlePromise: Promise<Paddle | undefined> | null = null;

async function fetchPaddleConfig(): Promise<PaddleConfigResponse> {
  const response = await api.get<PaddleConfigResponse>("/billing/paddle-config/");
  return response.data;
}

export async function getPaddle(): Promise<Paddle | undefined> {
  if (typeof window === "undefined") {
    return undefined;
  }

  if (!paddlePromise) {
    paddlePromise = (async () => {
      const config = await fetchPaddleConfig();
      return initializePaddle({
        token: config.clientSideToken,
        environment: config.environment,
        checkout: {
          settings: {
            displayMode: "overlay",
            theme: "light",
          },
        },
      });
    })();
  }

  return paddlePromise;
}

export function resetPaddleClient() {
  paddlePromise = null;
}
