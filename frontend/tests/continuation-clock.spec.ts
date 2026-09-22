import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const headers = { "X-Locus-Request": "1" };
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("locus-welcome-seen", "1"),
  );
});

test("exhausted Resume offers continuation with preserved criteria and start enabled", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/jobs", {
    headers,
    data: {
      name: "Fictional continuation regression",
      city: "Dolynska",
      country: "Ukraine",
    },
  });
  const job = await created.json();
  let extended = false;
  let submitted: any;
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    Object.assign(data, {
      status: extended ? "paused" : "completed",
      active_seconds: 1800.4,
      reason: extended
        ? "Search allowance updated. Ready to continue the saved queue."
        : "Достигнут лимит времени. Увеличьте бюджет, чтобы продолжить.",
      queue: { search: 3, fetch: 5, analyze: 1, review: 0 },
      continuation: {
        blocked_by: extended ? [] : ["time"],
        exhausted: extended ? [] : ["time"],
        pending_steps: 9,
      },
    });
    await route.fulfill({ response, json: data });
  });
  await page.route(`**/api/jobs/${job.id}/continue`, async (route) => {
    submitted = route.request().postDataJSON();
    // Exercise real persistence while preventing live model/network searches.
    const response = await route.fetch({
      postData: { ...submitted, start: false },
    });
    extended = response.ok();
    await route.fulfill({ response });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: /Fictional continuation regression/ })
    .first()
    .click();
  await expect(page.getByRole("timer")).toHaveText("30:00");
  await page
    .getByRole("button", { name: "Continue search", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("9 saved steps waiting");
  await expect(
    dialog.getByLabel("Start the local search after saving"),
  ).toBeChecked();
  await expect(
    dialog.getByLabel("Change criteria or add clues"),
  ).not.toBeChecked();
  await expect(dialog.getByLabel("Name", { exact: true })).toHaveCount(0);
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await dialog.getByRole("button", { name: "Save & continue search" }).click();
  await expect(dialog).not.toBeVisible();
  expect(submitted.start).toBe(true);
  expect(submitted.brief.city).toBe("Dolynska");
  expect(submitted.additional_budget.minutes).toBe(30);
  const saved = await (await request.get(`/api/jobs/${job.id}`)).json();
  expect(saved.revision).toBe(1);
  expect(saved.revisions).toHaveLength(1);
  await request.delete(`/api/jobs/${job.id}`, { headers });
});

test("timer ticks between polls, never resets on phase changes, and freezes on pause", async ({
  page,
  request,
}) => {
  await page.clock.install();
  const job = await (
    await request.post("/api/jobs", {
      headers,
      data: { name: "Fictional clock regression" },
    })
  ).json();
  let status = "running";
  let phase = "searching";
  let polls = 0;
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    polls++;
    Object.assign(data, {
      status,
      active_seconds: status === "running" ? 59 : 66,
      updated_at: new Date().toISOString(),
      settings_snapshot: { model: "fixture-local" },
      activity: {
        phase,
        target: "Fictional source",
        url: "https://example.org/profile",
        at: new Date().toISOString(),
      },
    });
    await route.fulfill({ response, json: data });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: /Fictional clock regression/ })
    .first()
    .click();
  const timer = page.getByRole("timer");
  await expect(timer).toHaveText("00:59");
  await expect(page.locator(".activity-actor")).toContainText("WEB MODULE");
  await page.clock.runFor(1250);
  await expect(timer).toHaveText("01:00");
  phase = "verifying";
  const before = polls;
  await page.clock.runFor(5000);
  await expect.poll(() => polls).toBeGreaterThan(before);
  await expect(page.locator(".activity-actor")).toContainText("LOCAL AI");
  await expect(timer).toHaveText("01:05");
  expect(
    await timer.evaluate((el) => getComputedStyle(el).fontVariantNumeric),
  ).toBe("tabular-nums");
  status = "paused";
  await page.clock.runFor(3000);
  await expect(page.locator(".research-activity")).toHaveClass(/still/);
  await expect(timer).toHaveText("01:06");
  await page.clock.runFor(5000);
  await expect(timer).toHaveText("01:06");
  await request.delete(`/api/jobs/${job.id}`, { headers });
});
