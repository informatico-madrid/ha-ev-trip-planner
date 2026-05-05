/**
 * auth.setup.soc.ts - Global Playwright Setup for Home Assistant E2E SOC Tests
 *
 * PURPOSE:
 * This file performs one-time authentication and integration setup before SOC E2E tests run.
 * It is executed as `globalSetup` in playwright-soc.config.ts and runs once per test session.
 *
 * WHAT IT DOES:
 * 1. Waits for Home Assistant to be fully started and reachable at http://localhost:8123
 * 2. Sets up the EV Trip Planner integration via REST API (if not already present)
 * 3. Authenticates via trusted_networks auth provider (no login form needed)
 * 4. Saves the authenticated browser state to playwright/.auth/user-soc.json so tests reuse it
 *
 * DIFFERENCE FROM auth.setup.ts:
 * - Saves auth state to a SEPARATE JSON file (user-soc.json) to avoid conflicts with main suite
 *
 * TRUSTED_NETWORKS BYPASS MECHANISM:
 * HA trusted_networks auto-logs-in requests from 127.0.0.1 / 172.17.0.0/16.
 * After navigating to the HA root, HA auto-redirects through the auth flow and lands
 * on /lovelace/0 (the default dashboard). Tests can then navigate to any panel.
 *
 * CONFIG FLOW (5 steps via REST API):
 * - Step 1 (user): vehicle_name = "test_vehicle"
 * - Step 2 (sensors): battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17, safety_margin_percent=20, t_base=24, soh_sensor=sensor.test_vehicle_soh
 * - Step 3 (emhass): planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24
 * - Step 4 (presence): charging_sensor = "input_boolean.test_ev_charging"
 * - Step 5 (notifications): empty (optional)
 */

import { chromium } from '@playwright/test';
import * as fs from 'fs';

const HA_URL = 'http://localhost:8123';
const HA_STARTUP_TIMEOUT_MS = 120_000;
const AUTH_DIR = 'playwright/.auth';
const AUTH_FILE = 'playwright/.auth/user-soc.json';

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

/**
 * Wait for a specific entity to appear in HA's state machine.
 * This is needed because input_booleans defined in configuration.yaml may take
 * some time to register after HA starts, especially in CI environments.
 */
async function waitForEntity(entityId: string, token: string, timeoutMs = 30_000): Promise<void> {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(`${HA_URL}/api/states`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
          const statesObj: Record<string, { entity_id: string }> = await response.json();
        const entityIds = Object.keys(statesObj);
        if (entityIds.some((id) => id === entityId)) {
          console.log(`[auth.setup] Entity "${entityId}" is available in HA`);
          return;
        }
      }
    } catch {
      // Entity check failed, keep polling
    }
    console.log(`[auth.setup] Entity "${entityId}" not yet available, waiting...`);
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  throw new Error(`[auth.setup] Timeout waiting for entity "${entityId}" to appear in HA`);
}

/**
 * Complete HA first-run onboarding if needed (creates dev/dev user).
 * Safe to call when already onboarded — detects and skips.
 */
async function ensureOnboarded(): Promise<void> {
  const clientId = `${HA_URL}/`;

  // Check if onboarding is needed
  const resp = await fetch(`${HA_URL}/api/onboarding`);
  if (!resp.ok) return; // If endpoint doesn't exist, already onboarded or not applicable

  const onboardingData = await resp.json() as { steps: Array<{ step: string; done: boolean }> };
  const steps = onboardingData.steps;
  const undone = steps.filter((s) => !s.done);
  if (undone.length === 0) {
    console.log('[auth.setup] HA already onboarded');
    return;
  }

  console.log('[auth.setup] Completing HA first-run onboarding (user=dev, password=dev)...');

  // Step 1: Create user
  const userResp = await fetch(`${HA_URL}/api/onboarding/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: clientId,
      language: 'en',
      name: 'Developer',
      username: 'dev',
      password: 'dev',
    }),
  });
  const userData = await userResp.json() as { auth_code?: string };
  if (!userData.auth_code) {
    console.log('[auth.setup] Onboarding user step failed or already done');
    return;
  }

  // Exchange auth code for token
  const params = new URLSearchParams({
    client_id: clientId,
    code: userData.auth_code,
    grant_type: 'authorization_code',
  });
  const tokenResp = await fetch(`${HA_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });
  const tokenData = await tokenResp.json() as { access_token?: string };
  if (!tokenData.access_token) return;

  const token = tokenData.access_token;
  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
  const body = JSON.stringify({ client_id: clientId });

  // Complete remaining onboarding steps
  await fetch(`${HA_URL}/api/onboarding/core_config`, { method: 'POST', headers, body }).catch(() => {});
  await fetch(`${HA_URL}/api/onboarding/analytics`, { method: 'POST', headers, body }).catch(() => {});
  await fetch(`${HA_URL}/api/onboarding/integration`, {
    method: 'POST', headers,
    body: JSON.stringify({ client_id: clientId, redirect_uri: `${HA_URL}/?auth_callback=1` }),
  }).catch(() => {});

  console.log('[auth.setup] Onboarding complete');
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
  const resp = await fetch(`${HA_URL}/api/config/config_entries`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await resp.json() as { entries: Array<{ domain: string; title: string }> };
  return data.entries.some((e) => e.domain === 'ev_trip_planner' && e.title === 'test_vehicle');
}

/** Set up the EV Trip Planner integration via config flow API */
async function setupIntegration(token: string): Promise<void> {
  console.log('[auth.setup] Setting up ev_trip_planner integration via REST API...');

  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  /**
   * POST helper that throws on non-2xx HTTP responses with a descriptive message.
   */
  const post = async (url: string, body: object): Promise<Record<string, unknown>> => {
    const r = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
    const data = await r.json() as Record<string, unknown>;
    if (!r.ok) {
      throw new Error(`[auth.setup] HTTP ${r.status} from ${url}: ${JSON.stringify(data)}`);
    }
    return data;
  };

  // HA loads integrations asynchronously after the HTTP server becomes available.
  // Retry the flow creation until ev_trip_planner is registered (up to 30 s).
  const FLOW_CREATE_RETRIES = 15;
  const FLOW_CREATE_DELAY_MS = 2000;

  let flow: Record<string, unknown> | undefined;
  for (let attempt = 1; attempt <= FLOW_CREATE_RETRIES; attempt++) {
    try {
      flow = await post(`${HA_URL}/api/config/config_entries/flow`, {
        handler: 'ev_trip_planner',
        show_advanced_options: false,
      });
      if (typeof flow.flow_id === 'string') {
        console.log(`[auth.setup] Config flow created (attempt ${attempt}), flow_id=${flow.flow_id}`);
        break;
      }
      // HA returned 200 but without a flow_id — treat as not-yet-ready
      throw new Error(`flow_id missing in response: ${JSON.stringify(flow)}`);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      if (attempt === FLOW_CREATE_RETRIES) {
        throw new Error(`[auth.setup] Could not create config flow after ${FLOW_CREATE_RETRIES} attempts: ${errMsg}`);
      }
      console.log(`[auth.setup] Flow creation attempt ${attempt} failed (${errMsg}), retrying in ${FLOW_CREATE_DELAY_MS}ms...`);
      await new Promise((resolve) => setTimeout(resolve, FLOW_CREATE_DELAY_MS));
    }
  }

  const flowId = flow?.flow_id;
  if (typeof flowId !== 'string') {
    throw new Error(`[auth.setup] Unexpected state: flow_id is not a string after retry loop`);
  }

  // Step 1: vehicle_name
  const step1 = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    vehicle_name: 'test_vehicle',
  });
  if (step1.type !== 'form' || step1.step_id !== 'sensors') {
    throw new Error(`[auth.setup] Step 1 unexpected response: ${JSON.stringify(step1)}`);
  }

  // Step 2: sensors (includes dynamic SOC capping fields)
  const step2 = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    battery_capacity_kwh: 60,
    charging_power_kw: 11,
    kwh_per_km: 0.17,
    safety_margin_percent: 20,
    soc_sensor: 'sensor.test_vehicle_soc',
    t_base: 24,
    soh_sensor: 'sensor.test_vehicle_soh',
  });
  if (step2.type !== 'form' || step2.step_id !== 'emhass') {
    throw new Error(`[auth.setup] Step 2 unexpected response: ${JSON.stringify(step2)}`);
  }

  // Step 3: EMHASS (accept defaults)
  const step3 = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    planning_horizon_days: 7,
    max_deferrable_loads: 50,
    index_cooldown_hours: 24,
  });
  if (step3.type !== 'form' || step3.step_id !== 'presence') {
    throw new Error(`[auth.setup] Step 3 unexpected response: ${JSON.stringify(step3)}`);
  }

  // Step 4: Presence — use input_boolean.test_ev_charging (always available in test env)
  const step4 = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    charging_sensor: 'input_boolean.test_ev_charging',
  });
  if (step4.type !== 'form' || step4.step_id !== 'notifications') {
    throw new Error(`[auth.setup] Step 4 unexpected response: ${JSON.stringify(step4)}`);
  }

  // Step 5: Notifications (optional — submit empty)
  const result = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {});

  if (result.type !== 'create_entry') {
    throw new Error(`[auth.setup] Integration setup failed: unexpected result type "${result.type}" — ${JSON.stringify(result)}`);
  }

  console.log(`[auth.setup] Integration "${result.title}" created successfully`);
}

/**
 * Wait for the panel's static assets (panel.js, lit-bundle.js) to be served.
 * async_setup_entry registers the static paths asynchronously after the config
 * flow creates the entry. In CI, there can be a race between the REST API
 * response ("create_entry") and the actual static-path registration.
 */
async function waitForPanelAssets(timeoutMs = 30_000): Promise<void> {
  const assets = [
    '/ev-trip-planner/panel.js',
    '/ev-trip-planner/lit-bundle.js',
  ];
  const start = Date.now();

  for (const asset of assets) {
    let ready = false;
    while (Date.now() - start < timeoutMs) {
      try {
        const resp = await fetch(`${HA_URL}${asset}`);
        if (resp.ok) {
          console.log(`[auth.setup] Asset "${asset}" is accessible (${resp.status})`);
          ready = true;
          break;
        }
        console.log(`[auth.setup] Asset "${asset}" returned ${resp.status}, retrying...`);
      } catch {
        // Not yet available
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    if (!ready) {
      console.warn(`[auth.setup] WARNING: Asset "${asset}" not accessible after ${timeoutMs}ms — tests may fail`);
    }
  }
}

async function globalSetup(): Promise<void> {
  console.log('[auth.setup] Waiting for Home Assistant to be ready...');
  await waitForHA();

  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // Complete first-run onboarding if needed (creates dev/dev user)
  await ensureOnboarded();

  // Get REST token to manage integration setup
  const token = await getAccessToken();

  // Wait for input_boolean.test_ev_charging to be available in HA
  // (it may take a few seconds after HA starts to register)
  await waitForEntity('input_boolean.test_ev_charging', token, 30_000);
  // Wait for SOH sensor to be available in HA
  await waitForEntity('sensor.test_vehicle_soh', token, 30_000);

  // Set up the integration only if not already done
  if (await isIntegrationSetUp(token)) {
    console.log('[auth.setup] ev_trip_planner integration already set up, skipping');
  } else {
    await setupIntegration(token);
  }

  // Wait for the panel's static assets to become available.
  // async_setup_entry registers static paths asynchronously after the config
  // flow completes. In CI, there can be a short delay before the JS module
  // is served. Poll until the panel.js returns 200 (up to 30 s).
  await waitForPanelAssets();

  // ---------------------------------------------------------------------------
  // TRUSTED_NETWORKS BYPASS — acquire browser session
  // ---------------------------------------------------------------------------
  // Navigate to HA root from 127.0.0.1. Trusted_networks auto-logs in and
  // redirects through the OAuth callback, landing on /lovelace/0.
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Log any console errors from the page for debugging
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[auth.setup] Browser console error: ${msg.text()}`);
    }
  });

  console.log('[auth.setup] Navigating to HA root for trusted_networks auth...');
  console.log('[auth.setup] Starting URL:', page.url());
  await page.goto(HA_URL);
  console.log('[auth.setup] Immediately after goto, URL is:', page.url());

  // HA redirects through auth and lands on lovelace or home — wait for either
  // HA 2026.3.x may redirect to "/" instead of "/lovelace" or "/home" — log for diagnosis
  try {
    console.log('[auth.setup] Waiting for /lovelace or /home (auth should redirect here)...');
    await page.waitForURL(/\/(lovelace|home)/, { timeout: 60_000 });
    console.log('[auth.setup] Auth successful, URL is:', page.url());
  } catch (err) {
    console.log('[auth.setup] waitForURL TIMEOUT. Final URL was:', page.url());
    // Capture all cookies to verify auth was actually set
    const cookies = await context.cookies();
    console.log('[auth.setup] Cookies after timeout:', cookies.map(c => `${c.name}=${c.value.substring(0,20)}...`).join(', '));
    throw err;
  }

  // Verify no login form appeared (trusted_networks bypassed it)
  const loginForm = page.locator('ha-auth-flow, [data-testid="login-form"]').first();
  if (await loginForm.isVisible({ timeout: 1_000 }).catch(() => false)) {
    throw new Error('[auth.setup] Login form appeared — trusted_networks bypass failed');
  }

  // Wait for HA frontend to load. In CI environments, HA may take longer
  // to render the frontend. We use a fixed wait plus URL stability check.
  // The sidebar (ha-sidebar, app-drawer-layout) may not appear in all CI
  // environments due to frontend resource constraints, so we proceed if
  // the URL is at /lovelace or /home and no login form is shown.
  console.log('[auth.setup] Waiting for HA frontend to settle...');
  await page.waitForLoadState('domcontentloaded').catch(() => {});
  await new Promise((resolve) => setTimeout(resolve, 5000));
  console.log('[auth.setup] HA frontend load wait complete (proceeding regardless)');

  // Save authenticated state for reuse in all tests
  await context.storageState({ path: AUTH_FILE });
  console.log(`[auth.setup] Auth state saved to ${AUTH_FILE}`);

  await browser.close();
  console.log('[auth.setup] Global setup complete');
}

export default globalSetup;
