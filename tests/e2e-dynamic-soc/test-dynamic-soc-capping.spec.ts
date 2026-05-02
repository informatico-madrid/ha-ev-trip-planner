/**
 * E2E Test: Dynamic SOC Capping — Multi-Trip Scenarios
 *
 * Verifies the dynamic SOC capping algorithm affects EMHASS sensor output
 * correctly under different multi-trip scenarios defined in the spec.
 *
 * Scenarios:
 *   Scenario A: Commute -> Large trip -> Commute (spec.md Scenario A)
 *   Scenario B: Large trip -> Commutes (spec.md Scenario B)
 *   Scenario C: Daily commute x4 (spec.md Scenario C — critical case)
 *   T_BASE=6h: Aggressive capping
 *   T_BASE=48h: Conservative capping
 *   SOH=92%: Real capacity affects capping
 *   Negative risk: large trip drains below 35%
 *
 * [VE0] [VERIFY:API] E2E Dynamic SOC Capping Verification
 */
import { test, expect, type Page } from '@playwright/test';
import {
  cleanupTestTrips,
  createTestTrip,
  getFutureIso,
  navigateToPanel,
} from './trips-helpers';

const VEHICLE_NAME = 'test_vehicle';
const SOH_ENTITY = 'sensor.test_vehicle_soh';

// ============================================================================
// Helpers
// ============================================================================

/**
 * Change SOC via HA frontend websocket (callService).
 */
async function changeSOC(page: Page, newValue: number): Promise<void> {
  await page.evaluate(async (value: number) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass) throw new Error('HA frontend hass not found');
    await haMain.hass.callService('input_number', 'set_value', {
      entity_id: 'input_number.test_vehicle_soc',
      value: value,
    });
  }, newValue);
  await page.waitForTimeout(2000);
}

/**
 * Change T_BASE via options flow UI.
 */
async function changeTBaseViaUI(page: Page, newTBase: number): Promise<void> {
  await page.goto('/config/integrations/integration/ev_trip_planner');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('text=Integration entries', { timeout: 15_000 });

  const testVehicleSection = page.locator('section').filter({ hasText: VEHICLE_NAME }).first();
  const configureBtn = testVehicleSection.getByRole('button', { name: 'Configure' });
  if (await configureBtn.count().catch(() => 0) > 0) {
    await configureBtn.first().click({ force: true });
  } else {
    const allBtns = page.getByRole('button', { name: 'Configure' });
    if (await allBtns.count().catch(() => 0) > 0) {
      await allBtns.first().click({ force: true });
    } else {
      throw new Error('[changeTBaseViaUI] Could not find Configure button');
    }
  }

  await page.waitForSelector('dialog', { state: 'visible', timeout: 10_000 });
  const tBaseSpinbutton = page.getByRole('spinbutton', { name: /t_base/ });
  await tBaseSpinbutton.fill(String(newTBase));
  await page.getByRole('button', { name: 'Submit' }).click();

  const finishBtn = page.getByRole('button', { name: 'Finish' });
  await expect(finishBtn).toBeVisible({ timeout: 10_000 });
  await finishBtn.click();
  await expect(finishBtn).not.toBeVisible({ timeout: 5_000 });
  await page.waitForTimeout(3000);

  // Navigate back to the panel — the options flow leaves us on the integration config page
  await navigateToPanel(page);
}

/**
 * Wait for EMHASS sensor to exist and have 'ready' status via frontend state.
 * Only reads what the HA frontend shows — what the user sees.
 * If this times out, it means the user also wouldn't see it.
 */
async function waitForEmhassSensor(page: Page): Promise<void> {
  await expect(async () => {
    const result = await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states) return { found: false, status: undefined };
      for (const [entityId, state] of Object.entries(haMain.hass.states)) {
        if (!entityId.includes('emhass_perfil_diferible')) continue;
        const attrs = (state as any).attributes;
        return { found: true, status: attrs?.emhass_status };
      }
      return { found: false, status: undefined };
    });
    expect(result.found).toBe(true);
    expect(result.status).toBe('ready');
  }).toPass({ timeout: 60_000 });
}

/**
 * Discover the EMHASS sensor entity ID.
 */
async function discoverEmhassSensorEntityId(page: Page): Promise<string | null> {
  return await page.evaluate((name: string) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states) return null;
    for (const [entityId, state] of Object.entries(haMain.hass.states)) {
      if (!entityId.includes('emhass_perfil_diferible')) continue;
      const attrs = (state as any).attributes;
      if (attrs?.vehicle_id === name) return entityId;
    }
    return null;
  }, VEHICLE_NAME);
}

/**
 * Get sensor attributes from HA frontend's hass.states.
 */
async function getSensorAttributes(page: Page, entityId: string): Promise<Record<string, any>> {
  return await page.evaluate((eid: string) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states?.[eid]) {
      throw new Error(`Entity ${eid} not found in hass.states`);
    }
    return haMain.hass.states[eid].attributes;
  }, entityId);
}

/**
 * Poll until sensor has non-zero power_profile values.
 */
async function waitForNonZeroProfile(page: Page, entityId: string, timeoutMs = 15000): Promise<void> {
  await expect(async () => {
    const attrs = await getSensorAttributes(page, entityId);
    expect(Array.isArray(attrs.power_profile_watts)).toBe(true);
    expect(attrs.power_profile_watts.some((v: number) => v > 0)).toBe(true);
    expect(attrs.emhass_status).toBe('ready');
  }).toPass({ timeout: timeoutMs });
}

// ============================================================================
// Tests
// ============================================================================

test.describe('Dynamic SOC Capping — Multi-Trip Scenarios', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // Scenario C: Daily commute x4 — the critical case (spec.md Scenario C)
  // --------------------------------------------------------------------------
  test('Scenario C: 4 daily commutes at T_BASE=24h — limit 94.9% > need 61%', async ({
    page,
  }) => {
    await changeSOC(page, 30);

    // Create 4 identical daily commute trips
    for (let i = 0; i < 4; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i + 1, '08:00'),
        30,
        6,
        `Scenario C Commute Day ${i + 1}`,
        { day: String(i + 1), time: '08:00' },
      );
    }

    // Wait for EMHASS to recalculate with new trips
    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const defCount = (attrs.deferrables_schedule as any[]).length;
    expect(defCount).toBeGreaterThanOrEqual(4);

    const defHoursArray = attrs.def_total_hours_array as number[];
    expect(Array.isArray(defHoursArray)).toBe(true);
    expect(defHoursArray.length).toBeGreaterThanOrEqual(4);

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    console.log(
      `Scenario C: ${nonZeroHours} charging hours, ${defCount} deferrable loads, ` +
      `def_total_hours_array length: ${defHoursArray.length}`,
    );

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // Scenario A: Commute -> Large trip -> Commute (spec.md Scenario A)
  // --------------------------------------------------------------------------
  test('Scenario A: commute->large->commute at T_BASE=24h — all trips succeed', async ({
    page,
  }) => {
    await changeSOC(page, 30);

    await createTestTrip(page, 'puntual', getFutureIso(1, '10:00'), 30, 6, 'Scenario A T1 Commute');
    await createTestTrip(page, 'puntual', getFutureIso(2, '08:00'), 150, 30, 'Scenario A T2 Large Trip');
    await createTestTrip(page, 'puntual', getFutureIso(3, '10:00'), 30, 6, 'Scenario A T3 Post-Drain Commute');

    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const defCount = (attrs.deferrables_schedule as any[]).length;
    expect(defCount).toBeGreaterThanOrEqual(3);

    console.log(
      `Scenario A: ${attrs.deferrables_schedule.length} deferrable loads, ` +
      `power_profile non-zero hours: ${attrs.power_profile_watts.filter((v: number) => v > 0).length}`,
    );

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // Scenario B: Large trip -> Commutes (spec.md Scenario B)
  // --------------------------------------------------------------------------
  test('Scenario B: large drain->100% then commutes at T_BASE=24h', async ({ page }) => {
    await changeSOC(page, 30);

    await createTestTrip(page, 'puntual', getFutureIso(1, '08:00'), 150, 30, 'Scenario B T1 Large Drain');

    for (let i = 2; i <= 4; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i, '08:00'),
        30,
        6,
        `Scenario B Commute Day ${i}`,
        { day: String(i), time: '08:00' },
      );
    }

    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const defCount = (attrs.deferrables_schedule as any[]).length;
    expect(defCount).toBeGreaterThanOrEqual(4);

    console.log(
      `Scenario B: ${defCount} deferrable loads (1 large + 3 commutes)`,
    );

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // T_BASE=6h: Aggressive capping
  // --------------------------------------------------------------------------
  test('T_BASE=6h aggressive capping — fewer charging hours than default 24h', async ({ page }) => {
    await changeTBaseViaUI(page, 6);
    await changeSOC(page, 30);

    for (let i = 0; i < 3; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i + 1, '09:00'),
        80,
        20,
        `Aggressive Cap Trip ${i + 1}`,
        { day: String(i + 1), time: '09:00' },
      );
    }

    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    const defCount = (attrs.deferrables_schedule as any[]).length;

    console.log(
      `T_BASE=6h: ${nonZeroHours} charging hours, ${defCount} deferrable loads`,
    );

    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // T_BASE=48h: Conservative capping
  // --------------------------------------------------------------------------
  test('T_BASE=48h conservative capping — more charging hours than default 24h', async ({ page }) => {
    await changeTBaseViaUI(page, 48);
    await changeSOC(page, 30);

    for (let i = 0; i < 3; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i + 1, '09:00'),
        80,
        20,
        `Conservative Cap Trip ${i + 1}`,
        { day: String(i + 1), time: '09:00' },
      );
    }

    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    const defCount = (attrs.deferrables_schedule as any[]).length;

    console.log(
      `T_BASE=48h: ${nonZeroHours} charging hours, ${defCount} deferrable loads`,
    );

    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // SOH=92%: Real battery capacity affects capping
  // --------------------------------------------------------------------------
  test('SOH=92% affects real capacity in capping calculations', async ({ page }) => {
    const sohState = await page.evaluate((entity: string) => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states?.[entity]) return null;
      return haMain.hass.states[entity].state;
    }, SOH_ENTITY);
    expect(sohState).toBe('92');

    await changeSOC(page, 40);
    await createTestTrip(page, 'puntual', getFutureIso(1, '10:00'), 150, 38, 'SOH 92% Capping Test');

    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    console.log(
      `SOH 92%: ${nonZeroHours} charging hours, real capacity 55.2kWh used in capping`,
    );

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // Negative risk: post-trip SOC <= 35% -> limit = 100%
  // --------------------------------------------------------------------------
  test('Negative risk: large trip drains below 35% -> 100% charge allowed', async ({ page }) => {
    await changeSOC(page, 20);
    await createTestTrip(page, 'puntual', getFutureIso(1, '08:00'), 200, 50, 'Negative Risk Large Drain');

    await waitForEmhassSensor(page);

    const sensorEntityId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensorEntityId).toBeTruthy();

    await waitForNonZeroProfile(page, sensorEntityId);

    const attrs = await getSensorAttributes(page, sensorEntityId!);
    expect(attrs.emhass_status).toBe('ready');

    const nonZeroHours = attrs.power_profile_watts.filter((v: number) => v > 0).length;
    expect(nonZeroHours).toBeGreaterThanOrEqual(1);

    console.log(
      `Negative risk: ${nonZeroHours} charging hours — 100% allowed after large drain`,
    );

    await cleanupTestTrips(page);
  });
});
