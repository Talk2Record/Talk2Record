import posthog from "posthog-js";

let initialized = false;

export function initAnalytics() {
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const host = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com";

  if (!key || initialized || typeof window === "undefined") {
    return;
  }

  posthog.init(key, {
    api_host: host,
    capture_pageview: true,
    persistence: "localStorage+cookie",
  });

  initialized = true;
}

export function trackEvent(event: string, properties?: Record<string, unknown>) {
  if (!initialized) {
    return;
  }

  posthog.capture(event, properties);
}
