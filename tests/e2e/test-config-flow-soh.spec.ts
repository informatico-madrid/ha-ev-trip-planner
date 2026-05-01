/**
 * E2E Test: Config Flow SOH and T_BASE Validation
 *
 * Verifies that the options flow for EV Trip Planner integration includes
 * the dynamic SOC capping fields (t_base and soh_sensor) and validates
 * their values correctly.
 *
 * User Stories:
 * - As a user, I want to configure SOH sensor in the integration options
 * - As a user, I want to configure T_BASE window for dynamic SOC capping
 * - As a user, I want validation that T_BASE is within 6-48h range
 *
 * [VE0] [VERIFY:API] E2E Config Flow Validation
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, cleanupTestTrips } from './trips-helpers';

const HA_URL = 'http://localhost:8123';

/** Helper: get an auth token via REST API */
async function getAuthToken(page: Page): Promise<string> {
  const resp = await page.evaluate(async () => {
    const haMain = document.querySelector('home-assistant') as any;
    return haMain?.hass?.auth?.hassAccessToken ?? '';
  });
  if (resp) return resp;

  // Fallback: use HA API to get token via trusted_networks
  // Already authenticated via storageState, so we can use the fetch from page context
  return await page.evaluate(async () => {
    // Get the token from the HA frontend state
    const haMain = document.querySelector('home-assistant') as any;
    if (haMain?.hass?.auth?.hassAccessToken) {
      return haMain.hass.auth.hassAccessToken;
    }
    // Try getting from the store
    return '';
  });
}

/** Helper: call HA REST API with auth token */
async function callHAApi(
  page: Page,
  endpoint: string,
  token: string,
  method: string = 'GET',
  body?: object,
): Promise<unknown> {
  return await page.evaluate(async ({ ep, tk, m, b }) => {
    const haMain = document.querySelector('home-assistant') as any;
    // Use the existing auth mechanism
    if (haMain?.hass?.auth?.fetchMessage) {
      // WebSocket-based — fall through to REST
    }
    const resp = await fetch(`${(window as any).__HA_BASE_URL || 'http://localhost:8123'}${ep}`, {
      method: m,
      headers: {
        'Authorization': `Bearer ${tk}`,
        'Content-Type': 'application/json',
      },
      body: b ? JSON.stringify(b) : undefined,
    });
    return resp.json();
  }, { ep: endpoint, tk: token, m: method, b: body });
}

/**
 * Discover the config flow entry for the existing test_vehicle integration
 * and return its entry_id.
 */
async function findIntegrationEntryId(
  page: Page,
  token: string,
): Promise<string | null> {
  return await page.evaluate(async ({ url, tk }) => {
    const resp = await fetch(`${url}/api/config/config_entries/entry`, {
      headers: { Authorization: `Bearer ${tk}` },
    });
    const entries: Array<{ entry_id: string; domain: string; title: string }> =
      await resp.json();
    const entry = entries.find(
      (e) => e.domain === 'ev_trip_planner' && e.title === 'test_vehicle',
    );
    return entry?.entry_id ?? null;
  }, { url: HA_URL, tk: token });
}

/**
 * Get the current options for the integration entry via the options flow.
 * Returns the form data from the first step.
 */
async function getOptionsFormData(
  page: Page,
  entryId: string,
  token: string,
): Promise<Record<string, unknown> | null> {
  return await page.evaluate(async ({ url, tk, entryId: eid }) => {
    // Create options flow
    const createResp = await fetch(`${url}/api/config/config_entries/flow`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ handler: 'ev_trip_planner', context: { source: 'options' } }),
    });
    const flow = await createResp.json();
    if (!flow.flow_id) return null;

    // Submit empty to get the first form
    const formResp = await fetch(`${url}/api/config/config_entries/flow/${flow.flow_id}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const form = await formResp.json();
    return form.data ? form.data : null;
  }, { url: HA_URL, tk: token, entryId });
}

test.describe('Config Flow SOH and T_BASE Validation', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('options flow should show t_base with default value 24 and soh_sensor field', async ({
    page,
  }) => {
    // Get auth token from page context
    const token = await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      return haMain?.hass?.auth?.hassAccessToken ?? '';
    });
    expect(token).toBeTruthy();

    // Step 1: Find the integration entry
    const entryId = await findIntegrationEntryId(page, token);
    expect(entryId).toBeTruthy();

    // Step 2: Open options flow and get form data
    const formData = await getOptionsFormData(page, entryId, token);
    expect(formData).toBeTruthy();

    // Step 3: Verify t_base field is present with correct default
    if (formData) {
      // t_base should be in the form data
      const tBase = (formData as any).t_base;
      expect(tBase).toBeDefined();
      // Default should be 24
      expect(tBase).toBe(24);

      // soh_sensor should be in the form data
      const sohSensor = (formData as any).soh_sensor;
      expect(sohSensor).toBeDefined();
      // Should match the entity configured in setup
      expect(sohSensor).toBe('sensor.test_vehicle_soh');
    }
  });

  test('options flow should validate t_base range (6-48 hours)', async ({
    page,
  }) => {
    const token = await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      return haMain?.hass?.auth?.hassAccessToken ?? '';
    });
    expect(token).toBeTruthy();

    const entryId = await findIntegrationEntryId(page, token);
    expect(entryId).toBeTruthy();

    // Open options flow and submit with invalid t_base (5, below minimum)
    const result = await page.evaluate(async ({ url, tk, eid }) => {
      const createResp = await fetch(`${url}/api/config/config_entries/flow`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ handler: 'ev_trip_planner', context: { source: 'options' } }),
      });
      const flow = await createResp.json();
      if (!flow.flow_id) return { error: 'no_flow_id' };

      // Submit with t_base=5 (below minimum of 6)
      const submitResp = await fetch(`${url}/api/config/config_entries/flow/${flow.flow_id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          battery_capacity: 60,
          charging_power: 11,
          consumption: 0.17,
          safety_margin: 20,
          t_base: 5,
          soh_sensor: 'sensor.test_vehicle_soh',
        }),
      });
      return submitResp.json();
    }, { url: HA_URL, tk: token, eid: entryId });

    // Should show a form with error (not a success or next step)
    expect((result as any).type).toBe('form');
    // Should have an error about t_base
    const errors = (result as any).errors;
    expect(errors).toBeDefined();
    expect(errors.base).toContain('invalid_t_base');

    // Now submit with valid t_base=48 (at maximum boundary)
    const result48 = await page.evaluate(async ({ url, tk }) => {
      const createResp = await fetch(`${url}/api/config/config_entries/flow`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ handler: 'ev_trip_planner', context: { source: 'options' } }),
      });
      const flow = await createResp.json();
      if (!flow.flow_id) return { error: 'no_flow_id' };

      const submitResp = await fetch(`${url}/api/config/config_entries/flow/${flow.flow_id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          battery_capacity: 60,
          charging_power: 11,
          consumption: 0.17,
          safety_margin: 20,
          t_base: 48,
          soh_sensor: 'sensor.test_vehicle_soh',
        }),
      });
      return submitResp.json();
    }, { url: HA_URL, tk: token });

    // t_base=48 should be accepted (go to next step or complete)
    const res48 = result48 as any;
    expect(res48.type).not.toBe('form');
  });

  test('options flow should accept t_base at minimum boundary (6 hours)', async ({
    page,
  }) => {
    const token = await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      return haMain?.hass?.auth?.hassAccessToken ?? '';
    });
    expect(token).toBeTruthy();

    const result = await page.evaluate(async ({ url, tk }) => {
      const createResp = await fetch(`${url}/api/config/config_entries/flow`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ handler: 'ev_trip_planner', context: { source: 'options' } }),
      });
      const flow = await createResp.json();
      if (!flow.flow_id) return { error: 'no_flow_id' };

      const submitResp = await fetch(`${url}/api/config/config_entries/flow/${flow.flow_id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          battery_capacity: 60,
          charging_power: 11,
          consumption: 0.17,
          safety_margin: 20,
          t_base: 6,
          soh_sensor: 'sensor.test_vehicle_soh',
        }),
      });
      return submitResp.json();
    }, { url: HA_URL, tk: token });

    // t_base=6 should be accepted
    const res = result as any;
    expect(res.type).not.toBe('form');
  });
});
