import { expect, test } from "@playwright/test";

test("marketing home page shows the Talk2Record value proposition", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Talk2Record/i);
  await expect(page.getByRole("heading", { name: /Turn WhatsApp voice notes into clean business records/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /Start free trial/i })).toHaveAttribute("href", "/register");
});

test("login page loads on the public auth route", async ({ page }) => {
  await page.goto("/login");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText(/Welcome back/i)).toBeVisible();
  await expect(page.getByRole("textbox", { name: /Work email/i })).toBeVisible();
});
