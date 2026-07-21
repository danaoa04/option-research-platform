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

test("documented offline quick-start flow remains navigable", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("link", { name: "Strategies" }).click();
  await expect(page.getByRole("heading", { name: "Strategy workspace" })).toBeVisible();
  await expect(page.getByText("Synthetic price — not current market data")).toBeVisible();

  await page.getByRole("link", { name: "Backtests" }).click();
  await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();
  await page.getByRole("button", { name: "configure" }).click();
  await expect(page.getByRole("heading", { name: "Strategy & data" })).toBeVisible();
  await page.getByRole("button", { name: "Review & run" }).click();
  await page.getByRole("button", { name: "Validate configuration" }).click();
  await expect(page.getByText("ready with warnings")).toBeVisible();

  await page.getByRole("link", { name: "Risk Lab" }).click();
  await expect(page.getByRole("heading", { name: "Scenarios" })).toBeVisible();
  await page.getByText(/Deterministic shock, not a forecast/).scrollIntoViewIfNeeded();

  await page.getByRole("button", { name: "reports" }).click();
  await page.getByRole("button", { name: "Preview report" }).click();
  await expect(page.getByLabel("Report preview")).toContainText("Provenance:");

  await page.getByRole("link", { name: "Diagnostics" }).click();
  await expect(page.getByText("release-candidate")).toBeVisible();
});

test("provider, research, replay, and release diagnostics remain available", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("link", { name: "Data", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Data providers" })).toBeVisible();
  await expect(page.getByText("ORATS", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Backtests" }).click();
  await page.getByRole("button", { name: "results" }).click();
  await expect(page.getByRole("heading", { name: "Results" })).toBeVisible();
  await expect(page.getByRole("table", { name: "Equity curve tabular alternative" }))
    .toContainText("$112,400");

  await page.getByRole("link", { name: "Replay" }).click();
  await expect(page.getByRole("heading", { name: "Replay", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Replay session replay-fixture-14" }))
    .toBeVisible();

  await page.getByRole("link", { name: "Diagnostics" }).click();
  await expect(page.getByText("1.0.0-rc.1")).toBeVisible();
  await expect(page.getByText("arm64")).toBeVisible();
  await expect(page.getByText("unsigned", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Generate diagnostic preview" }).click();
  await expect(page.locator("pre.diagnostic-preview")).toContainText('"schemaVersion": 1');
});
