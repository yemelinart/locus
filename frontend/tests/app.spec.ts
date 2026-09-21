import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("create, refine, extend, reload and delete a real persisted local search", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /За именем/ })).toBeVisible();
  await page.getByLabel("Имя и фамилия").fill("UI Test — Fictional Alex Rowan");
  await page.getByLabel("Город", { exact: true }).fill("Example City");
  await page
    .getByLabel("Что ещё вы знаете?")
    .fill("Synthetic UI test, no web search will be started.");
  await page
    .getByRole("button", { name: "Варианты имени, годы и источники" })
    .click();
  await page.getByLabel("Год рождения — от").fill("1985");
  await page.getByLabel("Год рождения — до").fill("1990");
  await page.getByRole("button", { name: "Создать поиск" }).click();
  await expect(
    page.getByRole("heading", {
      name: "UI Test — Fictional Alex Rowan",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("Новое уточнение")
    .fill("Public project: Example Language");
  await page.getByRole("button", { name: "Добавить ориентир" }).click();
  await expect(page.locator(".context-text")).toContainText("Example Language");
  await page.getByRole("button", { name: "Изменить бюджет" }).click();
  await page.getByRole("dialog").getByLabel("Время, мин").fill("90");
  await page.getByRole("button", { name: "Сохранить бюджет" }).click();
  await expect(page.locator(".budget-meter")).toContainText("90 мин");
  await page.reload();
  await page
    .getByRole("button", { name: /UI Test — Fictional Alex Rowan/ })
    .first()
    .click();
  await expect(page.locator(".context-text")).toContainText("Example Language");
  await page.getByRole("tab", { name: "Источники" }).click();
  await expect(
    page.getByText("Прочитанные и недоступные источники появятся здесь."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Удалить исследование" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Удалить", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: /За именем/ })).toBeVisible();
});

test("settings are accessible, reject remote AI, and persist local configuration", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Адрес сервера LM Studio")
    .fill("https://cloud.example/v1");
  await dialog.getByRole("button", { name: "Сохранить настройки" }).click();
  await expect(dialog.getByRole("alert")).toContainText("локальный");
  await dialog
    .getByLabel("Адрес сервера LM Studio")
    .fill("http://127.0.0.1:1234/v1");
  await dialog.getByRole("button", { name: "Сохранить настройки" }).click();
  await expect(dialog).not.toBeVisible();
});

test("mobile layout has no horizontal overflow or automatic external asset requests", async ({
  page,
}) => {
  const external: string[] = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:8421")) external.push(r.url());
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /За именем/ })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(external).toEqual([]);
});

test("main form and settings meet automated WCAG A and AA checks", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /За именем/ })).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});
