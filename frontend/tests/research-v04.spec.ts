import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("live phase, cited AI observation, withheld claims, reduced motion and empty conclusion", async ({
  page,
  request,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("locus-welcome-seen", "1"),
  );
  const response = await request.post("/api/jobs", {
    headers: { "X-Locus-Request": "1" },
    data: { name: "Fictional review observatory" },
  });
  const job = await response.json();
  let phase = "verifying",
    status = "running",
    empty = false;
  const facts = [
    {
      category: "education",
      statement: "Studied at Example University",
      quote: "Alex Rowan studied at Example University.",
    },
    {
      category: "organization",
      statement: "Incorrectly attributed role",
      quote: "Maya Chen works at Other Labs.",
    },
  ];
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    const result = await route.fetch();
    const data = await result.json();
    Object.assign(data, {
      status,
      activity: {
        phase,
        target: "Alex Rowan",
        url: "https://example.org/profile",
        at: new Date().toISOString(),
      },
      reason:
        status === "completed"
          ? "Finished the available search directions"
          : "",
      stats: { queries: 3, pages: 2, sources: 1, candidates: empty ? 0 : 1 },
      sources: [
        {
          id: "source",
          url: "https://example.org/profile",
          title: "Public university profile",
          status: "read",
          error: "",
          fetched_at: new Date().toISOString(),
        },
        {
          id: "blocked",
          url: "https://example.net/blocked",
          title: "Unavailable profile",
          status: "unavailable",
          error: "Access unavailable",
          fetched_at: new Date().toISOString(),
        },
      ],
      conclusion: {
        state: empty ? "no_supported_findings" : "possible",
        provisional: status !== "completed",
        promising_ids: empty ? [] : ["candidate"],
        reviewed_claims: empty ? 0 : 1,
        pending_cards: 0,
        conflicting_cards: 0,
        confirmed_cards: 0,
        read_sources: 1,
        unavailable_sources: 1,
      },
      candidates: empty
        ? []
        : [
            {
              id: "candidate",
              source_id: "source",
              status: "unreviewed",
              verification: {
                at: new Date().toISOString(),
                revision: 1,
                model: "fixture",
              },
              value: {
                name: "Alex Rowan",
                description: "",
                matches: [],
                contradictions: [],
                facts,
              },
              assessment: {
                level: "supported",
                name_quote: facts[0].quote,
                supported: [
                  {
                    kind: "education",
                    text: "Example University",
                    quote: facts[0].quote,
                  },
                ],
                missing: [{ kind: "organization", text: "Example Labs" }],
                flags: [],
                excluded: false,
                review_outdated: false,
                revision: 1,
                method: "semantic-review-v1",
                model_reviewed: true,
                audit_outdated: false,
                checked_facts: [{ ...facts[0], index: 0 }],
                withheld_count: 1,
                note: "The education clue is supported; the employer still needs checking.",
                note_facts: [0],
              },
            },
          ],
    });
    await route.fulfill({ response: result, json: data });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: /Fictional review observatory/ })
    .first()
    .click();
  await expect(page.locator(".research-activity")).toHaveAttribute(
    "data-phase",
    "verifying",
  );
  await expect(page.locator(".activity-note")).toContainText(
    "employer still needs checking",
  );
  await expect(page.locator(".activity-note a")).toHaveAttribute(
    "href",
    "https://example.org/profile",
  );
  await expect(page.locator(".research-conclusion")).toContainText(
    "A promising match to review",
  );
  await expect(page.locator(".candidate-card .facts")).not.toContainText(
    "Incorrectly attributed role",
  );
  await expect(page.locator(".candidate-card .facts")).toContainText(
    "Studied at Example University",
  );
  await page
    .getByRole("button", { name: "Pause animation", exact: true })
    .click();
  await expect(page.locator(".research-activity")).toHaveClass(/still/);
  await page
    .getByRole("button", { name: "Enable animation", exact: true })
    .click();
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    await page
      .locator(".orbit-a")
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: "../.qa/v04/review-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Change interface language" }).click();
  await expect(page.locator(".research-conclusion")).toContainText(
    "Есть совпадение",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../.qa/v04/review-mobile.png",
    fullPage: true,
  });
  status = "paused";
  await expect(page.locator(".research-activity")).toHaveClass(/still/, {
    timeout: 5000,
  });
  empty = true;
  phase = "finished";
  status = "completed";
  await expect(page.locator(".research-conclusion")).toContainText(
    "Обоснованного совпадения пока нет",
    { timeout: 5000 },
  );
  await expect(page.locator(".activity-note")).toHaveCount(0);
  await request.delete(`/api/jobs/${job.id}`, {
    headers: { "X-Locus-Request": "1" },
  });
});
