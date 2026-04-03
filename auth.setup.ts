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

  // Navigate to integrations page via sidebar
  console.log("[auth.setup] Navigating to integrations page via sidebar...");
  await page.getByRole("link", { name: "Integrations" }).click();
  await page.waitForURL("**/config/integrations**", { timeout: 30_000 });
  console.log("[auth.setup] Successfully navigated to integrations page");

  // Click "+ Add Integration" button to open integration search dialog
  console.log("[auth.setup] Clicking Add Integration button...");
  await page.getByRole("button", { name: /Add Integration/i }).click();
  // Wait for integration search dialog to appear
  await page.getByRole("dialog").waitFor({ state: "visible", timeout: 30_000 });
  console.log("[auth.setup] Add Integration dialog opened successfully");

  // Search for EV Trip Planner integration
  console.log("[auth.setup] Searching for EV Trip Planner integration...");
  const searchTextbox = page.getByRole("textbox", { name: /search/i });
  await searchTextbox.waitFor({ state: "visible", timeout: 30_000 });
  await searchTextbox.fill("EV Trip Planner");
  // Wait for search results to appear
  await page.getByText("EV Trip Planner").first().waitFor({ state: "visible", timeout: 30_000 });
  console.log("[auth.setup] EV Trip Planner integration found in search results");

  // Click on EV Trip Planner integration result to start Config Flow Step 1
  console.log("[auth.setup] Clicking EV Trip Planner integration result...");
  await page.getByText("EV Trip Planner").first().click();
  // Wait for Step 1 form (async_step_user) to appear
  await page.getByRole("textbox", { name: /vehicle_name/i }).waitFor({ state: "visible", timeout: 30_000 });
  console.log("[auth.setup] Config Flow Step 1 form appeared");

  // Fill vehicle_name field
  console.log("[auth.setup] Filling vehicle_name field with 'test_vehicle'...");
  await page.getByRole("textbox", { name: /vehicle_name/i }).fill("test_vehicle");

  // Submit Step 1 via Next/Submit button
  console.log("[auth.setup] Submitting Config Flow Step 1...");
  await page.getByRole("button", { name: /next|submit/i }).click();

  // Wait for Step 2 form (async_step_sensors) to appear
  console.log("[auth.setup] Waiting for Config Flow Step 2 form (sensors)...");
  await page.getByRole("textbox", { name: /battery_capacity_kwh/i }).waitFor({ state: "visible", timeout: 30_000 });
  console.log("[auth.setup] Config Flow Step 2 form appeared");

  // Fill sensor fields
  console.log("[auth.setup] Filling sensor fields...");
  await page.getByRole("textbox", { name: /battery_capacity_kwh/i }).fill("60");
  await page.getByRole("textbox", { name: /charging_power_kw/i }).fill("11");
  await page.getByRole("textbox", { name: /kwh_per_km/i }).fill("0.17");
  await page.getByRole("textbox", { name: /safety_margin_percent/i }).fill("20");
  console.log("[auth.setup] Sensor fields filled: battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17, safety_margin_percent=20");

  // Submit Step 2 via Next/Submit button
  console.log("[auth.setup] Submitting Config Flow Step 2...");
  await page.getByRole("button", { name: /next|submit/i }).click();

  // Wait for Step 3 form (async_step_emhass) to appear
  console.log("[auth.setup] Waiting for Config Flow Step 3 form (emhass)...");
  await page.getByRole("textbox", { name: /planning_horizon_days/i }).waitFor({ state: "visible", timeout: 30_000 });
  console.log("[auth.setup] Config Flow Step 3 form appeared");

  // Step 3 emhass fields: accept defaults (planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24)
  // planning_sensor is optional, leave empty
  console.log("[auth.setup] Accepting Step 3 default values: planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24");

  // Submit Step 3 via Next/Submit button
  console.log("[auth.setup] Submitting Config Flow Step 3...");
  await page.getByRole("button", { name: /next|submit/i }).click();

  // Wait for Step 4 form (async_step_presence) to appear
  console.log("[auth.setup] Waiting for Config Flow Step 4 form (presence)...");
  // The presence step has a charging_sensor entity selector
  // Wait for either the entity selector or a text field related to presence
  await page.waitForSelector("input, ha-entity-picker, ha-select", { timeout: 30_000 });
  console.log("[auth.setup] Config Flow Step 4 form appeared");

  // Step 4 presence fields: charging_sensor entity selector
  // Try to select an entity from the charging_sensor picker if available
  console.log("[auth.setup] Attempting to select charging_sensor entity...");
  const entityPicker = page.locator("ha-entity-picker").first();
  const entityPickerVisible = await entityPicker.isVisible().catch(() => false);

  if (entityPickerVisible) {
    // Open the entity picker dropdown
    await entityPicker.click();
    await page.waitForSelector("ha-list-item, .mdc-list-item, [data-entity]", { timeout: 10_000 }).catch(() => null);

    // Try to find and select a charging-related entity
    const listItems = page.locator("ha-list-item, .mdc-list-item, [data-entity]").first();
    if (await listItems.isVisible().catch(() => false)) {
      await listItems.click();
      console.log("[auth.setup] Charging sensor entity selected");
    } else {
      console.log("[auth.setup] No charging sensor entities available - proceeding without selection (server-side auto-select)");
    }
  } else {
    // If no entity picker found, check if there's a text input for charging_sensor
    const textInput = page.getByRole("textbox", { name: /charging_sensor/i });
    if (await textInput.isVisible().catch(() => false)) {
      // Leave empty for server-side auto-select
      console.log("[auth.setup] Charging sensor input found but empty - server will auto-select");
    } else {
      console.log("[auth.setup] No charging sensor field found - proceeding");
    }
  }

  // Submit Step 4 via Next/Finish button
  console.log("[auth.setup] Submitting Config Flow Step 4...");
  await page.getByRole("button", { name: /next|finish|submit/i }).click();

  // Save authenticated state for reuse in tests
  await context.storageState({ path: AUTH_FILE });
  console.log(`[auth.setup] Auth state saved to ${AUTH_FILE}`);

  await browser.close();
  console.log("[auth.setup] Global setup complete");
}

export default globalSetup;
