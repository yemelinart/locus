import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("review source links, combine criteria and undo", async ({
  page,
  request,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("locus-welcome-seen", "1"),
  );
  const created = await request.post("/api/jobs", {
    headers: { "X-Locus-Request": "1" },
    data: {
      name: "Fictional linked evidence",
      city: "Dolynska",
      country: "Ukraine",
    },
  });
  const job = await created.json();
  let status = "unreviewed";
  const ids = ["aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"];
  await page.route(`**/api/jobs/${job.id}/links/review`, async (route) => {
    const data = route.request().postDataJSON();
    expect([data.left_id, data.right_id]).toEqual(ids);
    status = data.status;
    await route.fulfill({ json: { ok: true } });
  });
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    const original = await route.fetch();
    const data = await original.json();
    data.status = "completed";
    data.stats = { queries: 1, pages: 2, sources: 2, candidates: 2 };
    data.sources = ["School profile", "Professional portfolio"].map(
      (title, i) => ({
        id: `s${i}`,
        title,
        url: `https://example.org/${i}`,
        status: "read",
        error: "",
        fetched_at: new Date().toISOString(),
      }),
    );
    const rows = [
      {
        field: "city",
        requested: "Dolynska",
        quote: "Alex Rowan studied design in Dolynska.",
      },
      {
        field: "country",
        requested: "Ukraine",
        quote: "Alex Rowan works as a designer in Ukraine.",
      },
    ];
    data.candidates = ids.map((id, i) => ({
      id,
      source_id: `s${i}`,
      status: "unreviewed",
      value: {
        name: "Alex Rowan",
        description: "",
        matches: [],
        contradictions: [],
        facts: [],
      },
      assessment: {
        identity_status: "unresolved",
        identity_checks: [
          { ...rows[i], relation: "supports", observed: rows[i].requested },
        ],
        level: "limited",
        model_reviewed: true,
        audit_outdated: false,
        checked_facts: [],
        withheld_count: 0,
        note: "",
        note_facts: [],
        name_quote: rows[i].quote,
        supported: [],
        missing: [],
        flags: [],
        excluded: false,
        review_outdated: false,
        revision: 1,
        method: "criteria-review-v3",
      },
    }));
    data.linkage = {
      proposals: [
        {
          left_id: ids[0],
          right_id: ids[1],
          from_source: "s0",
          to_source: "s1",
          context: "Alex Rowan: professional portfolio",
          kind: "hyperlink",
          status,
          stale: false,
        },
      ],
      groups:
        status === "confirmed"
          ? [
              {
                id: ids[0],
                candidate_ids: ids,
                identity_status: "eligible",
                source_count: 2,
                source_families: 1,
                identity_checks: rows.map((r, i) => ({
                  ...r,
                  relation: "supports",
                  evidence: [{ source_id: `s${i}`, quote: r.quote }],
                })),
              },
            ]
          : [],
    };
    data.conclusion = {
      state: status === "confirmed" ? "possible" : "no_supported_findings",
      linked_matches: status === "confirmed" ? 1 : 0,
      provisional: false,
      promising_ids: [],
      reviewed_claims: 0,
      pending_cards: 0,
      conflicting_cards: 0,
      confirmed_cards: 0,
      read_sources: 2,
      unavailable_sources: 0,
    };
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: /^Fictional linked evidence/ })
    .click();
  const panel = page.getByRole("region", { name: "Evidence across sources" });
  await expect(
    panel.getByRole("link", { name: "School profile" }),
  ).toBeVisible();
  await expect(panel.locator(".linked-profile")).toHaveCount(0);
  await panel
    .getByRole("button", { name: "Same person · combine evidence" })
    .click();
  await expect(
    panel.getByText("Alex Rowan · All required criteria supported"),
  ).toBeVisible();
  await expect(panel.locator(".linked-criterion")).toHaveCount(2);
  // The proposal details remain open after the action that adds a group.
  if (!(await panel.getByRole("button", { name: "Undo decision" }).isVisible()))
    await panel
      .locator("summary")
      .filter({ hasText: "Review source links" })
      .click();
  await panel.getByRole("button", { name: "Undo decision" }).click();
  await expect(panel.locator(".linked-profile")).toHaveCount(0);
  await panel.getByRole("button", { name: "Different people" }).click();
  await expect(
    panel.getByRole("button", { name: "Link rejected" }),
  ).toBeDisabled();
  await expect(panel.locator(".linked-profile")).toHaveCount(0);
  await panel
    .getByRole("button", { name: "Same person · combine evidence" })
    .click();
  await expect(panel.locator(".linked-profile")).toHaveCount(1);
  expect(
    (await new AxeBuilder({ page }).include(".source-links").analyze())
      .violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../.qa/v06/linked-mobile.png",
    fullPage: true,
  });
  await request.delete(`/api/jobs/${job.id}`, {
    headers: { "X-Locus-Request": "1" },
  });
});
