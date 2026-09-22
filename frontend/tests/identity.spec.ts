import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("required criteria separate matches, unknown links and conflicts", async ({
  page,
  request,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("locus-welcome-seen", "1"),
  );
  const response = await request.post("/api/jobs", {
    headers: { "X-Locus-Request": "1" },
    data: {
      name: "Fictional identity regression",
      city: "Dolynska",
      country: "Ukraine",
    },
  });
  const job = await response.json();
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    const original = await route.fetch();
    const data = await original.json();
    const statuses = ["eligible", "unresolved", "conflicting"];
    data.status = "completed";
    data.retryable_model_steps = 2;
    data.stats = { queries: 3, pages: 3, sources: 3, candidates: 3 };
    data.sources = statuses.map((s, i) => ({
      id: String(i),
      url: `https://example.org/${i}`,
      title: "Synthetic public profile",
      status: "read",
      error: "",
      fetched_at: new Date().toISOString(),
    }));
    data.candidates = statuses.map((state, i) => ({
      id: `c${i}`,
      source_id: String(i),
      status: "unreviewed",
      review_revision: 1,
      value: {
        name: ["Matching profile", "Unknown connection", "Conflicting year"][i],
        description: "",
        matches: [],
        contradictions: [],
        facts: [
          {
            statement: "Designer",
            quote: "Alex Rowan is a designer from Dolynska, Ukraine.",
            category: "professional_role",
          },
        ],
      },
      assessment: {
        identity_status: state,
        identity_checks: [
          {
            field: "city",
            requested: "Dolynska",
            relation:
              i === 0 ? "supports" : i === 1 ? "unknown" : "contradicts",
            quote:
              i === 0 ? "Alex Rowan is a designer from Dolynska, Ukraine." : "",
            observed: i === 0 ? "Dolynska" : "",
          },
        ],
        level: i === 0 ? "supported" : i === 1 ? "limited" : "conflicting",
        model_reviewed: true,
        audit_outdated: false,
        name_quote: "Alex Rowan is a designer.",
        supported: [],
        missing: [],
        flags: [],
        excluded: false,
        review_outdated: false,
        revision: 1,
        method: "criteria-review-v3",
        checked_facts: [
          {
            index: 0,
            statement: "Designer",
            quote: "Alex Rowan is a designer from Dolynska, Ukraine.",
            category: "professional_role",
          },
        ],
        withheld_count: 0,
        note: "",
        note_facts: [],
      },
    }));
    data.conclusion = {
      state: "possible",
      provisional: false,
      promising_ids: ["c0"],
      reviewed_claims: 1,
      pending_cards: 0,
      conflicting_cards: 1,
      confirmed_cards: 0,
      read_sources: 3,
      unavailable_sources: 0,
      unresolved_identity: 1,
      conflicting_identity: 1,
    };
    await route.fulfill({ response: original, json: data });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: /^Fictional identity regression/ })
    .click();
  await expect(page.locator(".candidate-card")).toHaveCount(1);
  await expect(page.locator(".candidate-card")).toContainText(
    "Matching profile",
  );
  await expect(page.locator(".candidate-card .review-label")).toHaveText(
    "Required criteria supported",
  );
  await expect(
    page.locator(".candidate-card .evidence-bars .filled"),
  ).toHaveCount(2);
  await expect(page.locator(".identity-criteria")).toContainText(
    "Supported by source",
  );
  await expect(page.locator(".research-conclusion")).toContainText(
    "outside matching results",
  );
  await expect(page.locator(".research-conclusion")).toContainText(
    "AI steps left unverified after invalid responses: 2",
  );
  await page
    .getByRole("combobox", { name: "Filter candidates" })
    .selectOption("unresolved");
  await expect(page.locator(".candidate-card")).toHaveCount(1);
  await expect(page.locator(".candidate-card")).toContainText(
    "Unknown connection",
  );
  await expect(page.locator(".candidate-card .review-label")).toHaveText(
    "Name only · identity unconfirmed",
  );
  await expect(
    page.locator(".candidate-card .evidence-bars .filled"),
  ).toHaveCount(0);
  await expect(page.locator(".candidate-card")).not.toContainText(
    "Possible match",
  );
  await expect(page.locator(".identity-unconfirmed-note")).toContainText(
    "not an identified match",
  );
  await page.getByRole("button", { name: "Change interface language" }).click();
  await expect(page.locator(".candidate-card .review-label")).toHaveText(
    "Только имя · личность не установлена",
  );
  await expect(page.locator(".research-conclusion")).toContainText(
    "Шагов ИИ осталось без проверки из-за неверных ответов: 2",
  );
  await page.getByRole("button", { name: "Изменить язык приложения" }).click();
  await expect(page.locator(".identity-criteria")).toContainText(
    "Connection unverified",
  );
  await page
    .getByRole("combobox", { name: "Filter candidates" })
    .selectOption("conflicting");
  await expect(page.locator(".candidate-card")).toContainText(
    "Conflicting year",
  );
  const a11y = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(a11y.violations).toEqual([]);
  await page.getByRole("button", { name: "Change interface language" }).click();
  await expect(page.locator(".identity-criteria")).toContainText(
    "Противоречие",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../.qa/v05/criteria-mobile.png",
    fullPage: true,
  });
  await request.delete(`/api/jobs/${job.id}`, {
    headers: { "X-Locus-Request": "1" },
  });
});
