import { expect, test } from "@playwright/test";
import { completeOnboarding, gotoAsAuthenticated, loginWithEmail } from "./helpers/auth";

test("unauthenticated dashboard visits redirect to login", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText(/welcome back/i)).toBeVisible();
});

test("email sign-in routes mock users to onboarding", async ({ page }) => {
  await loginWithEmail(page, { email: "owner@talk2record.app" });

  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByText(/finish onboarding/i)).toBeVisible();
  await expect(page.getByText(/Connect WhatsApp, validate a note, and confirm workspace defaults\./i)).toBeVisible();
});

test("onboarding completion opens the dashboard", async ({ page }) => {
  await loginWithEmail(page);
  await completeOnboarding(page);

  await expect(page.getByRole("heading", { name: /operations overview/i })).toBeVisible();
  await expect(page.getByText("Recent processing activity", { exact: true })).toBeVisible();
});

test("authenticated users can open the dashboard directly", async ({ page }) => {
  await gotoAsAuthenticated(page, "/dashboard");

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: /operations overview/i })).toBeVisible();
  await expect(page.getByText(/Latest records flowing from WhatsApp into Talk2Record\./i)).toBeVisible();
});
