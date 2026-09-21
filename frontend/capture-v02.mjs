import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";
await mkdir("../.qa/v02", { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
try {
  await page.goto("http://127.0.0.1:8420");
  await page.getByRole("heading", { name: /Behind a name/ }).waitFor();
  await page.screenshot({ path: "../.qa/v02/home.png", fullPage: true });
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Ocean", exact: true }).click();
  await dialog.getByRole("button", { name: "Dark", exact: true }).click();
  await page.screenshot({ path: "../.qa/v02/dark.png", fullPage: true });
  const violations = [];
  for (const name of ["Appearance", "Local AI", "Web search", "About"]) {
    await dialog.getByRole("tab", { name, exact: true }).click();
    if (name === "Local AI")
      await dialog.getByRole("button", { name: "Refresh models" }).click();
    if (name === "Web search")
      await page.screenshot({ path: "../.qa/v02/search.png", fullPage: true });
    const r = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    violations.push({
      name,
      violations: r.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    });
  }
  await dialog
    .getByRole("button", { name: "Close", exact: true })
    .last()
    .click();
  await page
    .locator(".job-link")
    .filter({ hasText: "Guido van Rossum" })
    .click();
  await page
    .getByRole("heading", { name: "Guido van Rossum", exact: true })
    .first()
    .waitFor();
  await page.screenshot({ path: "../.qa/v02/results.png", fullPage: true });
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  violations.push({
    name: "Results",
    violations: result.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
  });
  await page.getByRole("tab", { name: "Analysis", exact: true }).click();
  await page.getByRole("heading", { name: "Research at a glance" }).waitFor();
  await page.screenshot({ path: "../.qa/v02/analysis.png", fullPage: true });
  await page.getByRole("button", { name: /New research/ }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../.qa/v02/mobile.png", fullPage: true });
  console.log(
    JSON.stringify({
      errors,
      overflow: await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      violations,
    }),
  );
} finally {
  await browser.close();
}
