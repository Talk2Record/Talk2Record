import type { Page } from "@playwright/test";

export type PlaywrightAuthMode = "real-ui";

interface LoginCredentials {
  email: string;
  password: string;
}

interface AuthenticateOptions {
  mode?: PlaywrightAuthMode;
  credentials?: Partial<LoginCredentials>;
}

const defaultCredentials: LoginCredentials = {
  email: "owner@example.com",
  password: "T3stPassword!123",
};

function getAuthMode(mode?: PlaywrightAuthMode): PlaywrightAuthMode {
  const configuredMode = process.env.PLAYWRIGHT_AUTH_MODE as PlaywrightAuthMode | undefined;
  return mode || configuredMode || "real-ui";
}

async function waitForPathname(page: Page, matcher: RegExp) {
  await page.waitForFunction(
    ({ pattern }) => {
      return new RegExp(pattern).test(window.location.pathname);
    },
    { pattern: matcher.source }
  );
}

export async function loginWithEmail(page: Page, credentials: Partial<LoginCredentials> = {}) {
  const { email, password } = { ...defaultCredentials, ...credentials };

  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox", { name: /work email/i }).fill(email);
  await page.getByRole("textbox", { name: /^password$/i }).fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await waitForPathname(page, /^\/(onboarding|dashboard)$/);
}

export async function completeOnboarding(page: Page) {
  const enterDashboardButton = page.getByRole("button", { name: /i understand and continue/i });

  await enterDashboardButton.waitFor({ state: "visible" });
  await page.getByLabel(/you confirm you have consent to process voice data/i).check();
  await page.getByLabel(/you understand ai outputs may not be 100% accurate/i).check();
  await page.getByLabel(/you are responsible for verifying records/i).check();
  await enterDashboardButton.click();
  await waitForPathname(page, /^\/dashboard$/);
}

export async function gotoAsAuthenticated(
  page: Page,
  path = "/dashboard",
  { mode, credentials }: AuthenticateOptions = {}
) {
  getAuthMode(mode);

  await loginWithEmail(page, credentials);

  if (path === "/dashboard" && page.url().includes("/onboarding")) {
    await completeOnboarding(page);
    return;
  }

  if (path !== "/onboarding") {
    await page.goto(path);
  }
}
