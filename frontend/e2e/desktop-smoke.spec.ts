import { expect, test } from "@playwright/test";

test("offline workstation navigation and volatility fallback remain operational", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Synthetic demo data")).toBeVisible();
  await expect(page.getByText("Offline demo", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Volatility" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.getByRole("button", { name: "surface" }).click();
  await expect(page.getByRole("table", { name: "Complete volatility surface node table" }))
    .toContainText("missing");
  await expect(page.getByText(/Missing node: 64 DTE/)).toBeVisible();
});

test("command launcher exposes safe navigation only", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Meta+k");
  const dialog = page.getByRole("dialog", { name: "Command launcher" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("textbox", { name: "Find command" }).fill("diagnostics");
  await dialog.getByRole("button", { name: "Open diagnostics" }).click();
  await expect(page.getByRole("heading", { name: "Application diagnostics" })).toBeVisible();
});
