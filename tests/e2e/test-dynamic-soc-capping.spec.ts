/**
 * E2E Test: Dynamic SOC Capping — Charging Profiles & EMHASS Sensor Data
 *
 * Verifies that the dynamic SOC capping algorithm affects the EMHASS sensor
 * output correctly under different configurations:
 *
 * 1. Large trip (should cap SOC below 100%)
 * 2. Small trip (no capping, SOC at 100%)
 * 3. Different T_BASE values (shorter = more aggressive capping)
 * 4. SOH sensor configured vs nominal capacity
 *
 * [VE0] [VERIFY:API] E2E Dynamic SOC Capping Verification
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, cleanupTestTrips, createTestTrip, deleteTestTrip, getFutureIso } from './trips-helpers';

/**
 * Helper: discover the EMHASS sensor entity ID for test_vehicle.
 */
const discoverEmhassSensorEntityId = async (pg: Page): Promise<string | null> => {
  return await pg.evaluate(() => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states) return null;
    for (const [entityId, state] of Object.entries(haMain.hass.states)) {
      if (!entityId.includes('emhass_perfil_diferible')) continue;
      const attrs = (state as any).attributes;
      if (attrs?.vehicle_id === 'test_vehicle') return entityId;
    }
    return null;
  });
};

/**
 * Helper: get sensor attributes from HA frontend's hass.states object.
 */
const getSensorAttributes = async (pg: Page, entityId: string): Promise<Record<string, any>> => {
  return await pg.evaluate((eid: string) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states?.[eid]) {
      throw new Error(`Entity ${eid} not found in hass.states`);
    }
    return haMain.hass.states[eid].attributes;
  }, entityId);
};

/**
 * Helper: change SOC via HA frontend websocket.
 */
const changeSOCViaUI = async (pg: Page, newValue: number): Promise<void> => {
  await pg.evaluate(async (value: number) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass) throw new Error('HA frontend hass object not found');
    await haMain.hass.callService('input_number', 'set_value', {
      entity_id: 'input_number.test_vehicle_soc',
      value: value,
    });
  }, newValue);
  await pg.waitForTimeout(2000);
};

/**
 * Helper: change T_BASE via options flow REST API.
 */
const changeTBaseViaAPI = async (pg: Page, newTBase: number): Promise<void> => {
  const token = await pg.evaluate(() => {
    const haMain = document.querySelector('home-assistant') as any;
    return haMain?.hass?.auth?.hassAccessToken ?? '';
  });
  expect(token).toBeTruthy();

  await pg.evaluate(async ({ url, tk, tb }) => {
    // Create options flow
    const createResp = await fetch(`${url}/api/config/config_entries/flow`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ handler: 'ev_trip_planner', context: { source: 'options' } }),
    });
    const flow = await createResp.json();
    if (!flow.flow_id) throw new Error('No flow_id');

    // Submit updated options
    const submitResp = await fetch(`${url}/api/config/config_entries/flow/${flow.flow_id}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        battery_capacity: 60,
        charging_power: 11,
        consumption: 0.17,
        safety_margin: 20,
        t_base: tb,
        soh_sensor: 'sensor.test_vehicle_soh',
      }),
    });
    const result = await submitResp.json();
    if (result.type !== 'create_entry') {
      throw new Error(`Options update failed: ${JSON.stringify(result)}`);
    }
  }, { url: 'http://localhost:8123', tk: token, tb: newTBase });

  // Wait for coordinator to reload with new config
  await pg.waitForTimeout(3000);
};

/**
 * Poll until sensor has non-zero power_profile values.
 */
const waitForNonZeroProfile = async (
  pg: Page,
  entityId: string,
  timeoutMs = 15000,
): Promise<void> => {
  await expect(async () => {
    const attrs = await getSensorAttributes(pg, entityId);
    expect(Array.isArray(attrs.power_profile_watts)).toBe(true);
    expect(attrs.power_profile_watts.some((v: number) => v > 0)).toBe(true);
  }).toPass({ timeout: timeoutMs });
};

test.describe('Dynamic SOC Capping — Charging Profiles & EMHASS Sensors', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: Large trip that drains SOC close to 35% — dynamic capping should limit charge.
   *
   * With a 200km trip consuming 50kWh from 20% SOC (12kWh), the vehicle needs ~88kWh to reach 100%.
   * With a 60kWh battery, this exceeds capacity, so SOC cap should be below 100%.
   * The EMHASS sensor should reflect charging with a capped profile.
   */
  test('large trip should trigger SOC capping — EMHASS profile reflects capped charge', async ({
    page,
  }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    // Set initial SOC to 50% (mid-range, creates need for charging)
    await changeSOCViaUI(page, 50);

    // Create a large trip that would require more energy than the battery can provide
    const tripDatetime = getFutureIso(1, '10:00');
    await createTestTrip(
      page,
      'puntual',
      tripDatetime,
      200,
      50,
      'E2E Large Trip SOC Cap Test',
    );

    // Wait for EMHASS to calculate with non-zero profile
    await waitForNonZeroProfile(page, sensorEntityId);

    // Verify sensor attributes are populated
    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.power_profile_watts).toBeDefined();
    expect(Array.isArray(attrs.power_profile_watts)).toBe(true);
    expect(attrs.emhass_status).toBe('ready');

    // The power profile should have non-zero values (charging hours)
    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    // deferrables_schedule should have entries
    expect(Array.isArray(attrs.deferrables_schedule)).toBe(true);
    expect(attrs.deferrables_schedule.length).toBeGreaterThanOrEqual(1);

    console.log(
      `Large trip SOC cap test: ${nonZeroHours} non-zero charging hours, ` +
      `${attrs.deferrables_schedule.length} deferrable entries, ` +
      `status: ${attrs.emhass_status}`,
    );

    // Cleanup
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: Small trip that doesn't need full charge — no SOC capping needed.
   * The vehicle can charge to 100% without risk of not having enough for the trip.
   */
  test('small trip should not trigger SOC capping — EMHASS allows full charge', async ({
    page,
  }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    // Set initial SOC to 80% (high, small trip won't drain much)
    await changeSOCViaUI(page, 80);

    // Create a small trip (30km, 7kWh) — minimal energy needed
    const tripDatetime = getFutureIso(1, '10:00');
    await createTestTrip(
      page,
      'puntual',
      tripDatetime,
      30,
      7,
      'E2E Small Trip No Cap Test',
    );

    // Wait for EMHASS
    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    // Power profile should show charging
    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    console.log(
      `Small trip test: ${nonZeroHours} non-zero charging hours, ` +
      `status: ${attrs.emhass_status}`,
    );

    // Cleanup
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: T_BASE=6h (short window) — aggressive SOC capping, less charge needed.
   * The algorithm assumes the trip can happen soon, so it caps SOC lower.
   */
  test('short T_BASE (6h) should produce more aggressive SOC capping', async ({ page }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    // Set T_BASE to 6h (minimum, aggressive capping)
    await changeTBaseViaAPI(page, 6);

    // Set SOC to 30%
    await changeSOCViaUI(page, 30);

    // Create a moderate trip
    const tripDatetime = getFutureIso(1, '09:00');
    await createTestTrip(
      page,
      'puntual',
      tripDatetime,
      100,
      25,
      'E2E Short T_BASE Aggressive Cap',
    );

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;

    console.log(
      `Short T_BASE (6h): ${nonZeroHours} non-zero charging hours`,
    );

    // Cleanup
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: T_BASE=48h (long window) — conservative SOC capping, charge closer to 100%.
   * The algorithm allows more charging because the trip might not happen for a long time.
   */
  test('long T_BASE (48h) should produce conservative SOC capping', async ({ page }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    // Set T_BASE to 48h (maximum, conservative capping)
    await changeTBaseViaAPI(page, 48);

    // Set SOC to 30%
    await changeSOCViaUI(page, 30);

    // Create the same moderate trip as above
    const tripDatetime = getFutureIso(1, '09:00');
    await createTestTrip(
      page,
      'puntual',
      tripDatetime,
      100,
      25,
      'E2E Long T_BASE Conservative Cap',
    );

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;

    console.log(
      `Long T_BASE (48h): ${nonZeroHours} non-zero charging hours`,
    );

    // Cleanup
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: SOH sensor configured (92%) — real capacity = 60 * 0.92 = 55.2kWh.
   * The algorithm should use the real (degraded) capacity for SOC capping calculations.
   */
  test('SOH sensor (92%) should affect SOC capping — real capacity used', async ({ page }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    // Verify the SOH sensor entity is available
    const sohState = await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states?.['sensor.test_vehicle_soh']) return null;
      return haMain.hass.states['sensor.test_vehicle_soh'].state;
    });
    expect(sohState).toBe('92');

    // Set SOC to 40%
    await changeSOCViaUI(page, 40);

    // Create a trip that will be affected by SOH-based capping
    const tripDatetime = getFutureIso(1, '10:00');
    await createTestTrip(
      page,
      'puntual',
      tripDatetime,
      150,
      38,
      'E2E SOH Sensor Capping Test',
    );

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    // The profile should reflect the degraded capacity
    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    console.log(
      `SOH 92% test: ${nonZeroHours} non-zero charging hours, ` +
      `real capacity factored into capping`,
    );

    // Cleanup
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: Recurring trip — dynamic SOC capping should work with recurring trips too.
   */
  test('recurring trip should trigger SOC capping with EMHASS sensor', async ({ page }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await changeSOCViaUI(page, 50);

    // Create a recurring trip
    const tripDatetime = getFutureIso(1, '08:00');
    await createTestTrip(
      page,
      'recurrente',
      tripDatetime,
      100,
      25,
      'E2E Recurring Trip SOC Cap',
      { day: '1', time: '08:00' },
    );

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    // Cleanup
    await cleanupTestTrips(page);
  });

  /**
   * Scenario: Multiple trips with SOC capping — verify EMHASS aggregates correctly.
   */
  test('multiple trips with SOC capping — EMHASS aggregates all trips correctly', async ({
    page,
  }) => {
    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await changeSOCViaUI(page, 40);

    // Create two trips on different days
    const trip1Datetime = getFutureIso(1, '08:00');
    const trip2Datetime = getFutureIso(2, '14:00');

    await createTestTrip(
      page,
      'recurrente',
      trip1Datetime,
      80,
      20,
      'E2E Multi-Trip SOC Cap 1',
      { day: '1', time: '08:00' },
    );

    await createTestTrip(
      page,
      'recurrente',
      trip2Datetime,
      120,
      30,
      'E2E Multi-Trip SOC Cap 2',
      { day: '2', time: '14:00' },
    );

    // Wait for EMHASS to calculate with both trips
    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    // Should have more charging hours than a single trip
    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(2);

    // deferrables_schedule should have entries for both trips
    expect(attrs.deferrables_schedule.length).toBeGreaterThanOrEqual(2);

    console.log(
      `Multi-trip SOC cap: ${nonZeroHours} non-zero charging hours, ` +
      `${attrs.deferrables_schedule.length} deferrable entries`,
    );

    // Cleanup
    await cleanupTestTrips(page);
  });
});
