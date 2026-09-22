import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("blocked discovered profile is visible without an accepted identity", async ({
  page,
  request,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("locus-welcome-seen", "1"),
  );
  const r = await request.post("/api/jobs", {
    headers: { "X-Locus-Request": "1" },
    data: { name: "Alex Rowan", city: "Example City" },
  });
  const job = await r.json();
  await page.route(`**/api/jobs/${job.id}`, async (route) => {
    const original = await route.fetch();
    const data = await original.json();
    data.status = "completed";
    data.leads = [
      {
        id: "lead",
        url: "https://www.linkedin.com/in/fictional-alex-rowan",
        title: "Alex Rowan — Designer",
        snippet: "<script>window.injected = true</script> Public profile",
        query: '"Alex Rowan"',
        state: "unavailable",
        source_id: null,
        error: "robots",
        rank: 3,
      },
    ];
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await page.getByRole("button", { name: /^Alex Rowan/ }).click();
  const region = page.getByRole("region", {
    name: "Discovered links",
    exact: true,
  });
  await expect(region).toBeVisible();
  await expect(
    region.getByRole("link", { name: "Alex Rowan — Designer" }),
  ).toHaveAttribute("href", "https://www.linkedin.com/in/fictional-alex-rowan");
  await expect(region).toContainText("Automatic reading unavailable");
  await expect(
    page.getByRole("heading", { name: "No matches yet" }),
  ).toBeVisible();
  await region.getByText("Search preview · unverified").click();
  await expect(region).toContainText("<script>window.injected = true</script>");
  expect(
    await page.evaluate(
      () => (window as unknown as { injected?: boolean }).injected,
    ),
  ).toBeUndefined();
  expect(
    (await new AxeBuilder({ page }).include(".discovery-leads").analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Change interface language" }).click();
  await expect(
    page.getByRole("region", { name: "Найденные ссылки", exact: true }),
  ).toContainText("Автоматическое чтение недоступно");
});
