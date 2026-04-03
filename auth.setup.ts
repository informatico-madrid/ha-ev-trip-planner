/**
 * auth.setup.ts - Global Playwright Setup for Home Assistant E2E Tests
 *
 * PURPOSE:
 * This file performs one-time authentication and integration setup before E2E tests run.
 * It is executed as `globalSetup` in playwright.config.ts and runs once per test session.
 *
 * WHAT IT DOES:
 * 1. Waits for Home Assistant to be fully started and reachable at http://localhost:8123
 * 2. Bypasses authentication using the trusted_networks auth provider (no login form needed)
 * 3. Runs the EV Trip Planner Config Flow to set up the integration with default test values
 * 4. Saves the authenticated browser state to playwright/.auth/user.json so tests reuse it
 *
 * TRUSTED_NETWORKS BYPASS MECHANISM:
 * Home Assistant supports a trusted_networks auth provider that allows login without credentials
 * when the requesting IP is in the trusted_networks list (e.g., 127.0.0.1, 172.17.0.0/16 in Docker).
 * When the browser navigates to the HA root URL, HA automatically redirects to /home if the
 * incoming IP is trusted — no login form is presented. This is the ONLY permitted entry point
 * per the HA SPA routing pattern (never use page.goto() to navigate directly to internal panels).
 *
 * CONFIG FLOW STEPS (5 steps total):
 * - Step 1 (async_step_user): Vehicle name configuration
 * - Step 2 (async_step_sensors): Battery and charging sensor parameters
 * - Step 3 (async_step_emhass): EMHASS energy management settings
 * - Step 4 (async_step_presence): Presence detection sensor selection
 * - Step 5 (async_step_notifications): Optional notification configuration
 */

import { FullConfig, chromium } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const HA_URL = 'http://localhost:8123';
const HA_STARTUP_TIMEOUT_MS = 120_000;
const AUTH_DIR = 'playwright/.auth';
const AUTH_FILE = 'playwright/.auth/user.json';

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
  console.log('[auth.setup] Waiting for Home Assistant to be ready...');
  await waitForHA();

  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // ---------------------------------------------------------------------------
  // TRUSTED_NETWORKS BYPASS
  // ---------------------------------------------------------------------------
  // Home Assistant's trusted_networks auth provider automatically logs in users
  // from whitelisted IP ranges without presenting a login form. Since Playwright
  // runs from localhost (127.0.0.1) or within the Docker network (172.17.0.0/16),
  // HA recognizes the request as trusted and redirects directly to /home.
  // This eliminates the need to handle OAuth or username/password credentials.
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to HA root — this is the only allowed entry point per HA SPA pattern
  // HA SPA routing requires going through the root URL; direct navigation to
  // internal panels (e.g., /config/integrations) is not permitted by the router.
  await page.goto(HA_URL);
  await page.waitForURL('**/home/**', { timeout: 30_000 });

  // Verify trusted_networks bypass worked: no login form should appear
  const loginForm = page.getByRole('form').filter({ hasText: /login|sign in/i }).first();
  if (await loginForm.isVisible().catch(() => false)) {
    throw new Error('Login form appeared — trusted_networks bypass failed');
  }

  // Navigate to integrations page via sidebar
  console.log('[auth.setup] Navigating to integrations page via sidebar...');
  await page.getByRole('link', { name: 'Integrations' }).click();
  await page.waitForURL('**/config/integrations**', { timeout: 30_000 });
  console.log('[auth.setup] Successfully navigated to integrations page');

  // Click "+ Add Integration" button to open integration search dialog
  console.log('[auth.setup] Clicking Add Integration button...');
  await page.getByRole('button', { name: /Add Integration/i }).click();
  // Wait for integration search dialog to appear
  await page.getByRole('dialog').waitFor({ state: 'visible', timeout: 30_000 });
  console.log('[auth.setup] Add Integration dialog opened successfully');

  // Search for EV Trip Planner integration
  console.log('[auth.setup] Searching for EV Trip Planner integration...');
  const searchTextbox = page.getByRole('textbox', { name: /search/i });
  await searchTextbox.waitFor({ state: 'visible', timeout: 30_000 });
  await searchTextbox.fill('EV Trip Planner');
  // Wait for search results to appear
  await page.getByText('EV Trip Planner').first().waitFor({ state: 'visible', timeout: 30_000 });
  console.log('[auth.setup] EV Trip Planner integration found in search results');

  // Click on EV Trip Planner integration result to start Config Flow Step 1
  console.log('[auth.setup] Clicking EV Trip Planner integration result...');
  await page.getByText('EV Trip Planner').first().click();
  // Wait for Step 1 form (async_step_user) to appear
  await page.getByRole('textbox', { name: /vehicle_name/i }).waitFor({ state: 'visible', timeout: 30_000 });
  console.log('[auth.setup] Config Flow Step 1 form appeared');

  // ---------------------------------------------------------------------------
  // CONFIG FLOW STEP 1: vehicle_name (async_step_user)
  // ---------------------------------------------------------------------------
  // The first step collects the vehicle identifier. This name is used throughout
  // Home Assistant to identify the vehicle entity (e.g., sensor.ev_trip_planner_test_vehicle).
  // Test value: "test_vehicle" — hardcoded for CI consistency across runs.
  console.log('[auth.setup] Filling vehicle_name field with \'test_vehicle\'...');
  await page.getByRole('textbox', { name: /vehicle_name/i }).fill('test_vehicle');

  // Submit Step 1 via Next/Submit button
  console.log('[auth.setup] Submitting Config Flow Step 1...');
  await page.getByRole('button', { name: /next|submit/i }).click();

  // Wait for Step 2 form (async_step_sensors) to appear
  console.log('[auth.setup] Waiting for Config Flow Step 2 form (sensors)...');
  await page.getByRole('textbox', { name: /battery_capacity_kwh/i }).waitFor({ state: 'visible', timeout: 30_000 });
  console.log('[auth.setup] Config Flow Step 2 form appeared');

  // ---------------------------------------------------------------------------
  // CONFIG FLOW STEP 2: sensors (async_step_sensors)
  // ---------------------------------------------------------------------------
  // The second step configures battery and energy consumption parameters used for
  // trip range calculations and charging planning.
  // - battery_capacity_kwh: Total battery capacity in kilowatt-hours (test: 60 kWh)
  // - charging_power_kw: Maximum charging power in kilowatts (test: 11 kW)
  // - kwh_per_km: Energy consumption per kilometer (test: 0.17 kWh/km)
  // - safety_margin_percent: Reserved battery buffer to avoid full depletion (test: 20%)
  console.log('[auth.setup] Filling sensor fields...');
  await page.getByRole('textbox', { name: /battery_capacity_kwh/i }).fill('60');
  await page.getByRole('textbox', { name: /charging_power_kw/i }).fill('11');
  await page.getByRole('textbox', { name: /kwh_per_km/i }).fill('0.17');
  await page.getByRole('textbox', { name: /safety_margin_percent/i }).fill('20');
  console.log('[auth.setup] Sensor fields filled: battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17, safety_margin_percent=20');

  // Submit Step 2 via Next/Submit button
  console.log('[auth.setup] Submitting Config Flow Step 2...');
  await page.getByRole('button', { name: /next|submit/i }).click();

  // Wait for Step 3 form (async_step_emhass) to appear
  console.log('[auth.setup] Waiting for Config Flow Step 3 form (emhass)...');
  await page.getByRole('textbox', { name: /planning_horizon_days/i }).waitFor({ state: 'visible', timeout: 30_000 });
  console.log('[auth.setup] Config Flow Step 3 form appeared');

  // ---------------------------------------------------------------------------
  // CONFIG FLOW STEP 3: emhass (async_step_emhass)
  // ---------------------------------------------------------------------------
  // The third step configures EMHASS (Energy Management Home Assistant System) settings
  // for day-ahead energy planning and load deferral. All fields accept defaults.
  // - planning_horizon_days: Days ahead to plan energy usage (default: 7)
  // - max_deferrable_loads: Maximum number of deferrable loads (default: 50)
  // - index_cooldown_hours: Cooldown period between deferrals in hours (default: 24)
  // - planning_sensor: Optional sensor for external planning data (left empty)
  console.log('[auth.setup] Accepting Step 3 default values: planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24');

  // Submit Step 3 via Next/Submit button
  console.log('[auth.setup] Submitting Config Flow Step 3...');
  await page.getByRole('button', { name: /next|submit/i }).click();

  // Wait for Step 4 form (async_step_presence) to appear
  console.log('[auth.setup] Waiting for Config Flow Step 4 form (presence)...');
  // The presence step has a charging_sensor entity selector
  // Wait for either the entity selector or a text field related to presence
  await page.waitForSelector('input, ha-entity-picker, ha-select', { timeout: 30_000 });
  console.log('[auth.setup] Config Flow Step 4 form appeared');

  // ---------------------------------------------------------------------------
  // CONFIG FLOW STEP 4: presence (async_step_presence)
  // ---------------------------------------------------------------------------
  // The fourth step configures presence detection for home/away awareness.
  // - charging_sensor: Entity that indicates whether the vehicle is charging.
  //   This sensor is used to detect vehicle presence at home for load planning.
  //   If no entity is selected, the server will auto-select based on entity naming conventions.
  console.log('[auth.setup] Attempting to select charging_sensor entity...');
  const entityPicker = page.locator('ha-entity-picker').first();
  const entityPickerVisible = await entityPicker.isVisible().catch(() => false);

  if (entityPickerVisible) {
    // Open the entity picker dropdown
    await entityPicker.click();
    await page.waitForSelector('ha-list-item, .mdc-list-item, [data-entity]', { timeout: 10_000 }).catch(() => null);

    // Try to find and select a charging-related entity
    const listItems = page.locator('ha-list-item, .mdc-list-item, [data-entity]').first();
    if (await listItems.isVisible().catch(() => false)) {
      await listItems.click();
      console.log('[auth.setup] Charging sensor entity selected');
    } else {
      console.log('[auth.setup] No charging sensor entities available - proceeding without selection (server-side auto-select)');
    }
  } else {
    // If no entity picker found, check if there's a text input for charging_sensor
    const textInput = page.getByRole('textbox', { name: /charging_sensor/i });
    if (await textInput.isVisible().catch(() => false)) {
      // Leave empty for server-side auto-select
      console.log('[auth.setup] Charging sensor input found but empty - server will auto-select');
    } else {
      console.log('[auth.setup] No charging sensor field found - proceeding');
    }
  }

  // Submit Step 4 via Next/Finish button
  console.log('[auth.setup] Submitting Config Flow Step 4...');
  await page.getByRole('button', { name: /next|finish|submit/i }).click();

  // Wait for Step 5 form (async_step_notifications) to appear
  console.log('[auth.setup] Waiting for Config Flow Step 5 form (notifications)...');
  // The notifications step has optional fields: notification_service, notification_devices
  // Wait for either a textbox or the form to be visible
  await page.waitForSelector('textbox, ha-select, form', { timeout: 30_000 });
  console.log('[auth.setup] Config Flow Step 5 form appeared');

  // ---------------------------------------------------------------------------
  // CONFIG FLOW STEP 5: notifications (async_step_notifications)
  // ---------------------------------------------------------------------------
  // The fifth and final step configures optional notifications for trip events.
  // All fields are optional — if left empty, no notifications are sent.
  // - notification_service: MQTT service to use for notifications (optional)
  // - notification_devices: Device IDs to notify (optional)
  console.log('[auth.setup] Leaving notification fields empty (optional)');

  // Submit Step 5 via Finish button to complete Config Flow
  console.log('[auth.setup] Submitting Config Flow Step 5 (Finish)...');
  await page.getByRole('button', { name: /finish/i }).click();

  // Wait for redirect after Config Flow completes (integration installed)
  console.log('[auth.setup] Waiting for Config Flow to complete and redirect...');
  await page.waitForURL('**/config/integrations**', { timeout: 30_000 });
  console.log('[auth.setup] Config Flow completed successfully - integration installed');

  // Save authenticated state for reuse in tests
  // After storageState is saved, tests can use the authenticated session without
  // re-running globalSetup, dramatically reducing test execution time.
  await context.storageState({ path: AUTH_FILE });
  console.log(`[auth.setup] Auth state saved to ${AUTH_FILE}`);

  await browser.close();
  console.log('[auth.setup] Global setup complete');
}

export default globalSetup;
