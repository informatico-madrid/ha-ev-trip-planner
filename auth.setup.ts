/**
 * auth.setup.ts - Global Playwright Setup for Home Assistant E2E Tests
 *
 * PURPOSE:
 * This file performs one-time authentication and integration setup before E2E tests run.
 * It is executed as `globalSetup` in playwright.config.ts and runs once per test session.
 *
 * WHAT IT DOES:
 * 1. Waits for Home Assistant to be fully started and reachable at http://localhost:8123
 * 2. Completes first-run onboarding (creates dev/dev user) if needed
 * 3. Sets up the EV Trip Planner integration via REST API config flow
 * 4. Obtains auth tokens via REST API and injects them directly into storageState
 *    (no browser navigate needed — avoids WebSocket handshake dependency)
 *
 * KEY DESIGN DECISION:
 * The storageState (playwright/.auth/user.json) is built directly from REST API
 * tokens instead of navigating a browser and waiting for the HA frontend to
 * complete its WebSocket handshake. This is critical for CI where the HA frontend
 * can take 40-90s to initialize on resource-constrained runners, causing the
 * ha-launch-screen to persist and tests to timeout.
 *
 * CONFIG FLOW (5 steps via REST API):
 * - Step 1 (user): vehicle_name = "test_vehicle"
 * - Step 2 (sensors): battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17, safety_margin_percent=20
 * - Step 3 (emhass): planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24
 * - Step 4 (presence): charging_sensor = "input_boolean.test_ev_charging"
 * - Step 5 (notifications): empty (optional)
 */

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

/**
 * Wait for a specific entity to appear in HA's state machine.
 * This is needed because input_booleans defined in configuration.yaml may take
 * some time to register after HA starts, especially in CI environments.
 */
async function waitForEntity(entityId: string, timeoutMs = 30_000): Promise<void> {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(`${HA_URL}/api/states`, {
        headers: { Authorization: `Bearer ${await getAccessToken()}` },
      });
      if (response.ok) {
        const states = await response.json() as Array<{ entity_id: string }>;
        if (states.some((s) => s.entity_id === entityId)) {
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

  const steps = await resp.json() as Array<{ step: string; done: boolean }>;
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

/** Token data from HA OAuth token exchange */
interface TokenData {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

/**
 * Get auth tokens using the homeassistant auth provider (dev/dev).
 * Returns the full token data including refresh_token, needed for
 * building the storageState that the HA frontend expects.
 */
async function getTokens(): Promise<TokenData> {
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
  const tokenData = await tokenResp.json() as TokenData;
  return tokenData;
}

/** Convenience wrapper for code that only needs the access_token */
async function getAccessToken(): Promise<string> {
  const tokens = await getTokens();
  return tokens.access_token;
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

  // Step 2: sensors
  const step2 = await post(`${HA_URL}/api/config/config_entries/flow/${flowId}`, {
    battery_capacity_kwh: 60,
    charging_power_kw: 11,
    kwh_per_km: 0.17,
    safety_margin_percent: 20,
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

/**
 * Build the Playwright storageState file directly from REST API tokens.
 *
 * This is the KEY fix for CI: instead of navigating a browser to HA (which
 * requires the frontend to complete its WebSocket handshake — slow/unreliable
 * in CI), we construct the exact localStorage structure the HA frontend expects
 * from the OAuth token data obtained via REST API.
 *
 * The HA frontend stores tokens under "hassTokens" in localStorage with this
 * structure: { hassUrl, clientId, access_token, refresh_token, token_type, expires_in, expires }
 */
function buildStorageState(tokenData: TokenData): void {
  const hassTokens = {
    hassUrl: HA_URL,
    clientId: `${HA_URL}/`,
    access_token: tokenData.access_token,
    refresh_token: tokenData.refresh_token,
    token_type: tokenData.token_type || 'Bearer',
    expires_in: tokenData.expires_in,
    expires: Date.now() + tokenData.expires_in * 1000,
  };

  const storageState = {
    cookies: [],
    origins: [{
      origin: HA_URL,
      localStorage: [
        { name: 'hassTokens', value: JSON.stringify(hassTokens) },
      ],
    }],
  };

  fs.writeFileSync(AUTH_FILE, JSON.stringify(storageState, null, 2));
  console.log('[auth.setup] storageState written directly from REST API tokens (no browser needed)');
  console.log(`[auth.setup] Token expires in ${tokenData.expires_in}s, has refresh_token=${!!tokenData.refresh_token}`);
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

  // Get REST tokens for integration setup AND storageState injection
  const tokenData = await getTokens();
  const token = tokenData.access_token;

  // Wait for input_boolean.test_ev_charging to be available in HA
  // (it may take a few seconds after HA starts to register)
  await waitForEntity('input_boolean.test_ev_charging', 30_000);

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
  // BUILD STORAGE STATE — inject tokens directly (no browser needed)
  // ---------------------------------------------------------------------------
  // Get a FRESH set of tokens specifically for the browser storageState.
  // We need a separate token pair because the token used above for REST API
  // calls may have its refresh_token consumed during the setup process.
  const browserTokens = await getTokens();
  buildStorageState(browserTokens);

  console.log('[auth.setup] Global setup complete');
}

export default globalSetup;
