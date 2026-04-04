/**
 * auth.setup.ts - Global Playwright Setup for Home Assistant E2E Tests
 *
 * PURPOSE:
 * This file performs one-time authentication and integration setup before E2E tests run.
 * It is executed as `globalSetup` in playwright.config.ts and runs once per test session.
 *
 * WHAT IT DOES:
 * 1. Waits for Home Assistant to be fully started and reachable at http://localhost:8123
 * 2. Sets up the EV Trip Planner integration via REST API (if not already present)
 * 3. Authenticates via trusted_networks auth provider (no login form needed)
 * 4. Saves the authenticated browser state to playwright/.auth/user.json so tests reuse it
 *
 * TRUSTED_NETWORKS BYPASS MECHANISM:
 * HA trusted_networks auto-logs-in requests from 127.0.0.1 / 172.17.0.0/16.
 * After navigating to the HA root, HA auto-redirects through the auth flow and lands
 * on /lovelace/0 (the default dashboard). Tests can then navigate to any panel.
 *
 * CONFIG FLOW (5 steps via REST API):
 * - Step 1 (user): vehicle_name = "test_vehicle"
 * - Step 2 (sensors): battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17, safety_margin_percent=20
 * - Step 3 (emhass): planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24
 * - Step 4 (presence): charging_sensor = "input_boolean.test_ev_charging"
 * - Step 5 (notifications): empty (optional)
 */

import { chromium } from '@playwright/test';
import * as fs from 'fs';

const HA_URL = 'http://localhost:8123';
const HA_STARTUP_TIMEOUT_MS = 120_000;
const AUTH_DIR = 'playwright/.auth';
const AUTH_FILE = 'playwright/.auth/user.json';

/** Wait for HA API to respond with 401 (authenticated) or 200 (public) */
async function waitForHA(): Promise<void> {
  const start = Date.now();

  while (Date.now() - start < HA_STARTUP_TIMEOUT_MS) {
    try {
      const response = await fetch(`${HA_URL}/api/`);
      if (response.status === 401 || response.status === 200) {
        console.log(`[auth.setup] Home Assistant is ready (status ${response.status})`);
        return;
      }
    } catch {
      // HA not yet up, keep polling
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  throw new Error(`Home Assistant did not start within ${HA_STARTUP_TIMEOUT_MS}ms`);
}

/** Get an access token using the homeassistant auth provider (dev/dev) */
async function getAccessToken(): Promise<string> {
  const clientId = `${HA_URL}/`;

  // Start login flow
  const flowResp = await fetch(`${HA_URL}/auth/login_flow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: clientId,
      handler: ['homeassistant', null],
      redirect_uri: `${HA_URL}/?auth_callback=1`,
    }),
  });
  const flow = await flowResp.json() as { flow_id: string };

  // Submit credentials
  const credResp = await fetch(`${HA_URL}/auth/login_flow/${flow.flow_id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: clientId, username: 'dev', password: 'dev' }),
  });
  const cred = await credResp.json() as { result: string };

  // Exchange code for token
  const params = new URLSearchParams({
    client_id: clientId,
    code: cred.result,
    grant_type: 'authorization_code',
  });
  const tokenResp = await fetch(`${HA_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });
  const tokenData = await tokenResp.json() as { access_token: string };
  return tokenData.access_token;
}

/** Check if ev_trip_planner integration is already configured */
async function isIntegrationSetUp(token: string): Promise<boolean> {
  const resp = await fetch(`${HA_URL}/api/config/config_entries/entry`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const entries = await resp.json() as Array<{ domain: string; title: string }>;
  return entries.some((e) => e.domain === 'ev_trip_planner' && e.title === 'test_vehicle');
}

/** Set up the EV Trip Planner integration via config flow API */
async function setupIntegration(token: string): Promise<void> {
  console.log('[auth.setup] Setting up ev_trip_planner integration via REST API...');

  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  const post = async (url: string, body: object) => {
    const r = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
    return r.json();
  };

  // Start flow
  const flow = await post(`${HA_URL}/api/config/config_entries/flow`, {
    handler: 'ev_trip_planner',
    show_advanced_options: false,
  }) as { flow_id: string };
  const flowId = flow.flow_id;

  // Step 1: vehicle_name
  await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    vehicle_name: 'test_vehicle',
  });

  // Step 2: sensors
  await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    battery_capacity_kwh: 60,
    charging_power_kw: 11,
    kwh_per_km: 0.17,
    safety_margin_percent: 20,
  });

  // Step 3: EMHASS (accept defaults)
  await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    planning_horizon_days: 7,
    max_deferrable_loads: 50,
    index_cooldown_hours: 24,
  });

  // Step 4: Presence — use input_boolean.test_ev_charging (always available in test env)
  await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    charging_sensor: 'input_boolean.test_ev_charging',
  });

  // Step 5: Notifications (optional — submit empty)
  const result = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {}) as {
    type: string;
    title: string;
  };

  if (result.type !== 'create_entry') {
    throw new Error(`[auth.setup] Integration setup failed: unexpected result type "${result.type}"`);
  }

  console.log(`[auth.setup] Integration "${result.title}" created successfully`);
}

async function globalSetup(): Promise<void> {
  console.log('[auth.setup] Waiting for Home Assistant to be ready...');
  await waitForHA();

  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // Get REST token to manage integration setup
  const token = await getAccessToken();

  // Set up the integration only if not already done
  if (await isIntegrationSetUp(token)) {
    console.log('[auth.setup] ev_trip_planner integration already set up, skipping');
  } else {
    await setupIntegration(token);
  }

  // ---------------------------------------------------------------------------
  // TRUSTED_NETWORKS BYPASS — acquire browser session
  // ---------------------------------------------------------------------------
  // Navigate to HA root from 127.0.0.1. Trusted_networks auto-logs in and
  // redirects through the OAuth callback, landing on /lovelace/0.
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('[auth.setup] Navigating to HA root for trusted_networks auth...');
  await page.goto(HA_URL);

  // HA redirects through auth and lands on lovelace or home — wait for either
  await page.waitForURL(/\/(lovelace|home)/, { timeout: 30_000 });
  console.log(`[auth.setup] Authenticated: URL is ${page.url()}`);

  // Verify no login form appeared (trusted_networks bypassed it)
  const loginForm = page.locator('ha-auth-flow, [data-testid="login-form"]').first();
  if (await loginForm.isVisible({ timeout: 1_000 }).catch(() => false)) {
    throw new Error('[auth.setup] Login form appeared — trusted_networks bypass failed');
  }

  // Wait for HA frontend to fully load (sidebar visible)
  await page.locator('ha-sidebar, app-drawer-layout').first().waitFor({ state: 'visible', timeout: 30_000 });
  console.log('[auth.setup] HA frontend loaded');

  // Save authenticated state for reuse in all tests
  await context.storageState({ path: AUTH_FILE });
  console.log(`[auth.setup] Auth state saved to ${AUTH_FILE}`);

  await browser.close();
  console.log('[auth.setup] Global setup complete');
}

export default globalSetup;
