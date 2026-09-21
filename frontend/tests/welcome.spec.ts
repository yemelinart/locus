import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("first visit guide, setup, language, persistence and return from workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A name is a starting point." }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByRole("button", { name: "Set up local AI" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Local AI", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Change interface language" }).click();
  await expect(
    page.getByRole("heading", { name: "Имя — начало исследования." }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByText("Что остаётся локальным?", { exact: true }).click();
  await expect(
    page.getByText(/Поисковые запросы отправляются выбранным поисковикам/),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Открыть рабочее пространство" })
    .click();
  await expect(page.locator(".new-research")).toBeVisible();
  await page.reload();
  await expect(page.locator(".new-research")).toBeVisible();
  await page.getByRole("button", { name: "О программе и гайд" }).click();
  await expect(page.locator(".welcome-page")).toBeVisible();
});
