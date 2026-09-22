import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("locus-welcome-seen", "1"),
  );
});

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
  await page.getByRole("link", { name: /^PDF/ }).click();
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
  await page.route("**/api/models**", (route) =>
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

test("continue the same project with versioned criteria, export ZIP, and delete", async ({
  page,
  request,
}) => {
  const headers = { "X-Locus-Request": "1" };
  const created = await request.post("/api/jobs", {
    headers,
    data: {
      name: "Fictional archive test",
      context: "Original public context",
    },
  });
  const job = await created.json();
  await page.goto("/");
  await page
    .getByRole("button", { name: /Fictional archive test/ })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Refine & continue", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("School or university", { exact: true })
    .fill("Example University");
  await dialog
    .getByLabel("Organization or workplace", { exact: true })
    .fill("Example Labs");
  await dialog
    .getByLabel("Context and new clues")
    .fill("Updated public context");
  await expect(
    dialog.getByLabel("Start the local search after saving"),
  ).not.toBeChecked();
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.screenshot({
    path: "../.qa/v03/continuation.png",
    fullPage: true,
  });
  await dialog.getByRole("button", { name: "Save new criteria" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.locator(".context-text")).toContainText(
    "Updated public context",
  );
  const result = await (await request.get(`/api/jobs/${job.id}`)).json();
  expect(result.id).toBe(job.id);
  expect(result.revision).toBe(2);
  expect(result.brief.evidence_clues).toHaveLength(2);
  expect(result.status).toBe("paused");
  await page.getByRole("tab", { name: /History/ }).click();
  await expect(page.getByText("Criteria v2", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Export project archive" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("dialog").getByRole("link", { name: /ZIP/ }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(`locus-${job.id}.zip`);
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page
    .getByRole("button", { name: "Delete research", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("local project folder");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect
    .poll(async () => (await request.get(`/api/jobs/${job.id}`)).status())
    .toBe(404);
});

test("evidence support explains quotes, missing clues and archived candidates", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/jobs", {
    headers: { "X-Locus-Request": "1" },
    data: { name: "Fictional evidence test" },
  });
  const job = await created.json();
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const data = await response.json();
    data.sources = [
      {
        id: "source",
        url: "https://example.org/profile",
        title: "Example University profile",
        status: "read",
        error: "",
        fetched_at: new Date().toISOString(),
      },
    ];
    const value = {
      name: "Alex Rowan",
      description: "Synthetic public profile for interface testing",
      matches: [],
      contradictions: [],
      facts: [
        {
          category: "education",
          statement: "Studied at Example University",
          quote: "Alex Rowan studied at Example University.",
        },
      ],
    };
    const assessment = {
      level: "supported",
      name_quote: value.facts[0].quote,
      supported: [
        {
          kind: "education",
          text: "Example University",
          quote: value.facts[0].quote,
        },
      ],
      missing: [{ kind: "organization", text: "Example Labs" }],
      flags: [],
      excluded: false,
      review_outdated: false,
      revision: 1,
      method: "quote-clues-v1",
    };
    data.candidates = [
      {
        id: "candidate",
        source_id: "source",
        status: "unreviewed",
        value,
        assessment,
      },
      {
        id: "archived",
        source_id: "source",
        status: "unreviewed",
        value: { ...value, name: "Archived Alex" },
        assessment: { ...assessment, level: "excluded", excluded: true },
      },
    ];
    await route.fulfill({ response, json: data });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: /Fictional evidence test/ })
    .first()
    .click();
  // A legacy quote-only assessment must not appear as a positive identity check.
  await expect(page.locator(".evidence-meter summary strong")).toHaveText(
    "Identity check pending",
  );
  await expect(page.locator(".evidence-bars .filled")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Archived Alex", exact: true }),
  ).not.toBeVisible();
  await page.locator(".evidence-meter summary").click();
  await expect(page.locator(".evidence-explanation")).toContainText(
    "not an identity probability",
  );
  await expect(page.locator(".evidence-explanation")).toContainText(
    "Example Labs",
  );
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.screenshot({ path: "../.qa/v03/evidence.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByLabel("Filter candidates").selectOption("archived");
  await expect(
    page.getByRole("heading", { name: "Archived Alex", exact: true }),
  ).toBeVisible();
  await request.delete(`/api/jobs/${job.id}`, {
    headers: { "X-Locus-Request": "1" },
  });
});

test("local providers reset incompatible controls, discover models and explain generation without changing search", async ({
  page,
  request,
}) => {
  const headers = { "X-Locus-Request": "1" };
  const original = await (await request.get("/api/settings")).json();
  const initial = {
    ...original,
    model_provider: "lmstudio",
    model_url: "http://127.0.0.1:1234/v1",
    model: "qwen3-local",
    inference_mode: "qwen_no_thinking",
    reasoning: "default",
    structured_output: false,
    results_per_query: 17,
    search_region: "tr-tr",
    safesearch: "on",
  };
  await request.put("/api/settings", { headers, data: initial });
  const probes: any[] = [];
  await page.route("**/api/models**", async (route) => {
    const body =
      route.request().method() === "POST"
        ? route.request().postDataJSON()
        : initial;
    probes.push(body);
    const ollama = body.model_provider === "ollama";
    await route.fulfill({
      json: {
        connected: true,
        error: "",
        models: ollama ? ["qwen3:8b"] : ["qwen3-local"],
        capabilities:
          ollama && body.model
            ? [
                {
                  key: "qwen3:8b",
                  name: "Qwen 3",
                  instances: [],
                  max_context: 32768,
                  reasoning_options: ["off", "on"],
                  reasoning_default: "on",
                  architecture: "qwen3",
                },
              ]
            : [],
      },
    });
  });
  try {
    await page.goto("/");
    await page.getByRole("button", { name: "Settings", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("tab", { name: "Local AI", exact: true }).click();
    await dialog.getByLabel("AI provider").selectOption("ollama");
    await expect(
      dialog.getByLabel("Server address", { exact: true }),
    ).toHaveValue("http://127.0.0.1:11434");
    await expect(dialog.getByLabel("Model", { exact: true })).toHaveValue("");
    await expect(dialog.getByLabel("Inference mode")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Refresh models" }).click();
    await dialog.getByLabel("Model", { exact: true }).selectOption("qwen3:8b");
    await expect(
      dialog.getByLabel("Thinking level").locator("option"),
    ).toHaveCount(3);
    await dialog
      .getByRole("button", { name: "Apply recommended settings" })
      .click();
    await expect(dialog.getByLabel("Thinking level")).toHaveValue("off");
    await dialog.getByText("Manual settings & guide", { exact: true }).click();
    await expect(dialog).toContainText("not more factual");
    await expect(dialog).toContainText("can damage exact quotes and names");
    await expect(dialog.getByLabel("Top K", { exact: true })).toBeVisible();
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(scan.violations).toEqual([]);
    await page.screenshot({
      path: "../.qa/providers/ollama-guide.png",
      fullPage: true,
    });
    await dialog.getByRole("button", { name: "Save settings" }).click();
    await expect(dialog).not.toBeVisible();
    const saved = await (await request.get("/api/settings")).json();
    expect(saved.model_provider).toBe("ollama");
    expect(saved.inference_mode).toBe("chat");
    expect(saved.model).toBe("qwen3:8b");
    expect(saved.results_per_query).toBe(17);
    expect(saved.search_region).toBe("tr-tr");
    expect(saved.safesearch).toBe("on");
    expect(
      probes.some(
        (p) => p.model_provider === "ollama" && p.model === "qwen3:8b",
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Settings", exact: true }).click();
    await dialog.getByRole("tab", { name: "Local AI", exact: true }).click();
    await dialog.getByLabel("AI provider").selectOption("openai_compatible");
    await expect(
      dialog.getByLabel("Server address", { exact: true }),
    ).toHaveValue("http://127.0.0.1:8080/v1");
    await expect(dialog.getByLabel("Thinking level")).toHaveCount(0);
    await dialog.getByLabel("AI provider").selectOption("ollama");
    await expect(dialog.getByLabel("Model", { exact: true })).toHaveValue(
      "qwen3:8b",
    );
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  } finally {
    await request
      .put("/api/settings", { headers, data: original })
      .catch(() => {});
  }
});

test("a late model probe cannot populate a newly selected provider", async ({
  page,
}) => {
  let release: (() => void) | undefined;
  let started: (() => void) | undefined;
  const began = new Promise<void>((resolve) => {
    started = resolve;
  });
  await page.route("**/api/models/probe", async (route) => {
    started?.();
    await new Promise<void>((resolve) => {
      release = resolve;
    });
    await route.fulfill({
      json: {
        connected: true,
        error: "",
        models: ["stale-lmstudio-model"],
        capabilities: [],
      },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: "Local AI", exact: true }).click();
  await dialog.getByRole("button", { name: "Refresh models" }).click();
  await began;
  await dialog.getByLabel("AI provider").selectOption("ollama");
  const completed = page.waitForResponse("**/api/models/probe");
  release?.();
  await completed;
  await expect(
    dialog.getByLabel("Model", { exact: true }).locator("option"),
  ).toHaveCount(1);
  await expect(dialog).toContainText("Not connected");
});
