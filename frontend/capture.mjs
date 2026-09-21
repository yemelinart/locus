import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

await mkdir("../.qa", { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:8420");
  await page.getByRole("heading", { name: /За именем/ }).waitFor();
  await page.screenshot({ path: "../.qa/desktop.png", fullPage: true });
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.screenshot({ path: "../.qa/settings.png", fullPage: true });
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  await page.getByRole("button", { name: /Guido van Rossum/ }).click();
  await page.getByRole("heading", { name: "Guido van Rossum", exact: true }).first().waitFor();
  await page.screenshot({ path: "../.qa/results.png", fullPage: true });
  await page.getByRole("button", { name: /Новый поиск/ }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../.qa/mobile.png", fullPage: true });
  console.log(
    JSON.stringify({
      pageErrors: errors,
      mobileOverflow: await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    }),
  );
} finally {
  await browser.close();
}
