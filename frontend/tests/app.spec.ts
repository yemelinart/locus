import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("create, refine, extend, reload and delete a real persisted local search", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Behind a name/ }),
  ).toBeVisible();
  await page.getByLabel("Full name").fill("UI Test — Fictional Alex Rowan");
  await page.getByLabel("City", { exact: true }).fill("Example City");
  await page
    .getByLabel("What else do you know?")
    .fill("Synthetic UI test, no web search will be started.");
  await page
    .getByRole("button", { name: "Name variants, years & sources" })
    .click();
  await page.getByLabel("Birth year — from").fill("1985");
  await page.getByLabel("Birth year — to").fill("1990");
  await page.getByRole("button", { name: "Create research" }).click();
  await expect(
    page.getByRole("heading", {
      name: "UI Test — Fictional Alex Rowan",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("New clarification")
    .fill("Public project: Example Language");
  await page.getByRole("button", { name: "Add clue" }).click();
  await expect(page.locator(".context-text")).toContainText("Example Language");
  await page.getByRole("button", { name: "Edit budget" }).click();
  await page.getByRole("dialog").getByLabel("Time, min").fill("90");
  await page.getByRole("button", { name: "Save budget" }).click();
  await expect(page.locator(".budget-meter")).toContainText("90 min");
  await page.reload();
  await page
    .getByRole("button", { name: /UI Test — Fictional Alex Rowan/ })
    .first()
    .click();
  await expect(page.locator(".context-text")).toContainText("Example Language");
  await page.getByRole("tab", { name: "Sources" }).click();
  await expect(
    page.getByText("Read and unavailable sources will appear here."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Delete research" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: /Behind a name/ }),
  ).toBeVisible();
});

test("settings are accessible, reject remote AI, and persist local configuration", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Local AI", exact: true }).click();
  await dialog
    .getByLabel("LM Studio server address")
    .fill("https://cloud.example/v1");
  await dialog.getByRole("button", { name: "Save settings" }).click();
  await expect(dialog.getByRole("alert")).toContainText("local");
  await dialog
    .getByLabel("LM Studio server address")
    .fill("http://127.0.0.1:1234/v1");
  await dialog.getByRole("button", { name: "Save settings" }).click();
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
  await expect(
    page.getByRole("heading", { name: /Behind a name/ }),
  ).toBeVisible();
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
  await expect(
    page.getByRole("heading", { name: /Behind a name/ }),
  ).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});

test("language, palette and brightness persist without losing a draft", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Full name").fill("Draft Alex");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Interface language").selectOption("ru");
  await expect(
    dialog.getByRole("heading", { name: "Настройки", exact: true }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Океан", exact: true }).click();
  await dialog.getByRole("button", { name: "Тёмная", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-tone", "dark");
  await dialog
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await expect(page.getByLabel("Имя и фамилия")).toHaveValue("Draft Alex");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page.locator("html")).toHaveAttribute("data-palette", "ocean");
  await page.getByRole("button", { name: "Изменить язык приложения" }).click();
  await expect(page.getByLabel("Full name")).toBeVisible();
});

test("name hypotheses, sidebar analysis, PDF download and deletion", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Full name").fill("Сергей Емелин");
  await page
    .getByRole("button", { name: "Name variants, years & sources" })
    .click();
  await page
    .getByRole("button", { name: "Preview spelling hypotheses" })
    .click();
  await expect(page.locator(".name-preview")).toContainText("Sergey Yemelin");
  await expect(page.locator(".name-preview")).toContainText("Sergii Iemielin");
  await page
    .getByLabel("Could the surname have changed?")
    .selectOption("known");
  await page
    .getByLabel("Known previous full names")
    .pressSequentially("Sergey Yemelin, Sergii Iemielin");
  await expect(page.getByLabel("Known previous full names")).toHaveValue(
    "Sergey Yemelin, Sergii Iemielin",
  );
  await page.getByRole("button", { name: "Create research" }).click();
  await page
    .getByRole("button", { name: "Analysis: Сергей Емелин", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Research at a glance" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Export: Сергей Емелин", exact: true })
    .click();
  const pending = page.waitForEvent("download");
  await page.getByRole("link", { name: /PDF/ }).click();
  const download = await pending;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  expect(await download.failure()).toBeNull();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Delete: Сергей Емелин", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(
    page.locator(".history-row").filter({ hasText: "Сергей Емелин" }),
  ).toHaveCount(0);
});

test("native thinking follows reported capabilities and search controls show actual availability", async ({
  page,
}) => {
  await page.route("**/api/models*", (route) =>
    route.fulfill({
      json: {
        connected: true,
        error: "",
        models: ["test-local"],
        capabilities: [
          {
            key: "test-local",
            name: "Test model",
            instances: [],
            max_context: 16384,
            reasoning_options: ["off", "low", "xhigh"],
            reasoning_default: "low",
            architecture: "test",
          },
        ],
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  let dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Local AI", exact: true }).click();
  await dialog.getByLabel("Model", { exact: true }).selectOption("test-local");
  await dialog.getByLabel("Inference mode").selectOption("lmstudio");
  await dialog.getByLabel("Thinking level").selectOption("xhigh");
  expect(
    await dialog
      .getByLabel("Thinking level")
      .locator("option")
      .allTextContents(),
  ).toEqual(["Model default (low)", "off", "low", "xhigh"]);
  await dialog.getByRole("button", { name: "Save settings" }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Local AI", exact: true }).click();
  await expect(dialog.getByLabel("Thinking level")).toHaveValue("xhigh");
  await dialog.getByRole("tab", { name: "Web search", exact: true }).click();
  await expect(
    dialog.locator(".engine-card").filter({ hasText: "Google" }),
  ).toBeEnabled();
  await expect(
    dialog.locator(".engine-card").filter({ hasText: "Bing" }),
  ).toBeDisabled();
  await dialog.getByRole("tab", { name: "About", exact: true }).click();
  await expect(dialog).toContainText("VibeCoded by Sergey Yemelin");
  await expect(dialog).toContainText("ChatGPT 6 Astra");
});

test("all palettes and tones keep accessible text contrast", async ({
  page,
}) => {
  await page.goto("/");
  for (const palette of ["forest", "ocean", "sand", "graphite"])
    for (const tone of ["light", "soft", "dark"]) {
      await page.evaluate(
        ({ palette, tone }) => {
          document.documentElement.dataset.palette = palette;
          document.documentElement.dataset.tone = tone;
        },
        { palette, tone },
      );
      const result = await new AxeBuilder({ page })
        .withRules(["color-contrast"])
        .analyze();
      expect(result.violations, `${palette} ${tone}`).toEqual([]);
    }
});
