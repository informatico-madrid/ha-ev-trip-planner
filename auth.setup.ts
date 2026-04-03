import { FullConfig, chromium } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const HA_URL = "http://localhost:8123";
const HA_STARTUP_TIMEOUT_MS = 120_000;
const AUTH_DIR = "playwright/.auth";
const AUTH_FILE = "playwright/.auth/user.json";

async function waitForHA(): Promise<void> {
  const start = Date.now();

  while (Date.now() - start < HA_STARTUP_TIMEOUT_MS) {
    try {
      const response = await fetch(HA_URL);
      if (response.ok) {
        console.log(`Home Assistant is ready at ${HA_URL}`);
        return;
      }
    } catch (error) {
      console.error(`[auth.setup] HA connection failed: ${error instanceof Error ? error.message : String(error)}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  throw new Error(`Home Assistant did not start within ${HA_STARTUP_TIMEOUT_MS}ms`);
}

async function globalSetup(config: FullConfig): Promise<void> {
  console.log("[auth.setup] Waiting for Home Assistant to be ready...");
  await waitForHA();

  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // trusted_networks bypass: navigate to root URL, HA redirects to /home if IP is trusted
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to HA root — this is the only allowed entry point per HA SPA pattern
  await page.goto(HA_URL);
  await page.waitForURL("**/home/**", { timeout: 30_000 });

  // Verify trusted_networks bypass worked: no login form should appear
  const loginForm = page.getByRole("form").filter({ hasText: /login|sign in/i }).first();
  if (await loginForm.isVisible().catch(() => false)) {
    throw new Error("Login form appeared — trusted_networks bypass failed");
  }

  // Save authenticated state for reuse in tests
  await context.storageState({ path: AUTH_FILE });
  console.log(`[auth.setup] Auth state saved to ${AUTH_FILE}`);

  await browser.close();
  console.log("[auth.setup] Global setup complete");
}

export default globalSetup;
