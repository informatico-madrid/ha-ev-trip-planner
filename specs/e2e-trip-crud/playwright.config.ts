import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  retries: 1,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
  ],
  globalSetup: "./auth.setup.ts",
  globalTeardown: "./globalTeardown.ts",
  use: {
    baseURL: "http://localhost:8123",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});