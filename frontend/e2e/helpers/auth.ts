import type { Page } from "@playwright/test";
import type { AuthUser } from "@/types/platform";

export type PlaywrightAuthMode = "mock-storage" | "mock-ui" | "real-ui";

interface LoginCredentials {
  email: string;
  password: string;
}

interface AuthenticateOptions {
  mode?: PlaywrightAuthMode;
  credentials?: Partial<LoginCredentials>;
  user?: Partial<AuthUser>;
}

const authStorageKey = "talk2record-auth";

const defaultCredentials: LoginCredentials = {
  email: "owner@talk2record.app",
  password: "testing123",
};

const defaultMockUser: AuthUser = {
  id: "playwright_user",
  email: defaultCredentials.email,
  name: "Playwright Owner",
  company: "Talk2Record Demo Workspace",
  role: "owner",
  onboardingCompleted: true,
};

function getAuthMode(mode?: PlaywrightAuthMode): PlaywrightAuthMode {
  const configuredMode = process.env.PLAYWRIGHT_AUTH_MODE as PlaywrightAuthMode | undefined;
  return mode || configuredMode || "mock-storage";
}

function createPersistedAuthState(user: AuthUser) {
  return JSON.stringify({
    state: { user },
    version: 0,
  });
}

async function waitForPathname(page: Page, matcher: RegExp) {
  await page.waitForFunction(
    ({ pattern }) => {
      return new RegExp(pattern).test(window.location.pathname);
    },
    { pattern: matcher.source }
  );
}

async function waitForLoginPageInteractivity(page: Page) {
  const showPasswordButton = page.getByRole("button", { name: /show password/i });
  const hidePasswordButton = page.getByRole("button", { name: /hide password/i });

  await page.waitForLoadState("networkidle");
  await showPasswordButton.waitFor({ state: "visible" });
  await showPasswordButton.click();
  await hidePasswordButton.waitFor({ state: "visible" });
  await hidePasswordButton.click();
  await showPasswordButton.waitFor({ state: "visible" });
}

export async function seedAuthenticatedSession(page: Page, userOverrides: Partial<AuthUser> = {}) {
  const user = { ...defaultMockUser, ...userOverrides };
  const persistedState = createPersistedAuthState(user);

  await page.addInitScript(
    ({ key, value }) => {
      window.sessionStorage.setItem(key, value);
    },
    { key: authStorageKey, value: persistedState }
  );
}

export async function loginWithEmail(page: Page, credentials: Partial<LoginCredentials> = {}) {
  const { email, password } = { ...defaultCredentials, ...credentials };

  await page.goto("/login");
  await waitForLoginPageInteractivity(page);
  await page.getByRole("textbox", { name: /work email/i }).fill(email);
  await page.getByRole("textbox", { name: /^password$/i }).fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await waitForPathname(page, /^\/(onboarding|dashboard)$/);
}

export async function completeOnboarding(page: Page) {
  const enterDashboardButton = page.getByRole("button", { name: /enter dashboard/i });

  await enterDashboardButton.waitFor({ state: "visible" });
  await enterDashboardButton.click();
  await waitForPathname(page, /^\/dashboard$/);
}

export async function gotoAsAuthenticated(
  page: Page,
  path = "/dashboard",
  { mode, credentials, user }: AuthenticateOptions = {}
) {
  const authMode = getAuthMode(mode);

  if (authMode === "mock-storage") {
    await seedAuthenticatedSession(page, user);
    await page.goto(path);
    return;
  }

  await loginWithEmail(page, credentials);

  if (path === "/dashboard" && page.url().includes("/onboarding")) {
    await completeOnboarding(page);
    return;
  }

  if (path !== "/onboarding") {
    await page.goto(path);
  }
}
