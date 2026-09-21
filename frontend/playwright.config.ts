import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8421",
    browserName: "chromium",
    channel: process.env.LOCUS_BROWSER_CHANNEL,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "../.venv/bin/python -m uvicorn locus.api:create_app --factory --host 127.0.0.1 --port 8421",
    url: "http://127.0.0.1:8421/api/health",
    reuseExistingServer: false,
    env: {
      LOCUS_DATA_DIR: join(tmpdir(), `locus-browser-tests-${process.pid}`),
      LOCUS_PORT: "8421",
    },
  },
});
