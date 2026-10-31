import { defineConfig } from "@playwright/test";

// The app must already be running with LLM_MOCK=true. Nothing here starts it,
// so the same suite runs against a local uvicorn and against the Docker container.
export default defineConfig({
  testDir: "./e2e",
  // Specs share one app and one portfolio, so they run one at a time, in file order.
  workers: 1,
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8010",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
