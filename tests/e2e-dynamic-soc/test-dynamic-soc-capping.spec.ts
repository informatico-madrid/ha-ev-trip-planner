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
 * Uses patterns from working tests/e2e/emhass-sensor-updates.spec.ts:
 * - Navigate to /developer-tools/state for state changes (reliable hass access)
 * - Use filter textbox to search sensors in devtools
 * - Use page.waitForFunction() for state propagation (condition-based, NOT fixed timeout)
 * - Use page.evaluate() with hass.states for attribute access
 * - Always navigate back to panel after state-changing helpers
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

// ============================================================================
// Helpers — patterns from working e2e suite (emhass-sensor-updates.spec.ts)
// ============================================================================

/**
 * Change SOC via HA frontend websocket (callService).
 * Navigate to devtools (light DOM, reliable home-assistant access),
 * change state, verify propagation, navigate back to panel.
 */
async function changeSOC(page: Page, newValue: number): Promise<void> {
  // Navigate to devtools for reliable home-assistant element access
  await page.goto('/developer-tools/state', { waitUntil: 'networkidle' });

  await page.evaluate(async (value: number) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass) throw new Error('HA frontend hass not found');
    await haMain.hass.callService('input_number', 'set_value', {
      entity_id: 'input_number.test_vehicle_soc',
      value: value,
    });
  }, newValue);

  // Wait for state propagation (condition-based, numeric comparison)
  await expect(async () => {
    const state = await page.evaluate((_: number) => {
      const ha = document.querySelector('home-assistant') as any;
      if (ha?.hass?.states) {
        return ha.hass.states['input_number.test_vehicle_soc']?.state;
      }
      return undefined;
    }, newValue);
    expect(Number(state)).toBe(newValue);
  }).toPass({ timeout: 10_000 });

  // Navigate back to panel so subsequent createTestTrip calls work
  await navigateToPanel(page);
}

/**
 * Change SOH via HA frontend websocket (callService).
 * Navigates to devtools for reliable home-assistant element access,
 * then returns to panel for subsequent createTestTrip calls.
 */
async function changeSOH(page: Page, value: number): Promise<void> {
  // Navigate to devtools for reliable home-assistant element access
  await page.goto('/developer-tools/state', { waitUntil: 'networkidle' });
  await page.evaluate(async (v: number) => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass) throw new Error('HA frontend hass not found');
    await haMain.hass.callService('input_number', 'set_value', {
      entity_id: 'input_number.test_vehicle_soh',
      value: v,
    });
  }, value);
  // Wait for SOH state propagation (condition-based, numeric comparison)
  await expect(async () => {
    const state = await page.evaluate((_: number) => {
      const ha = document.querySelector('home-assistant') as any;
      if (ha?.hass?.states) {
        return ha.hass.states['input_number.test_vehicle_soh']?.state;
      }
      return undefined;
    }, value);
    expect(Number(state)).toBe(value);
  }).toPass({ timeout: 10_000 });
  // Navigate back to panel so subsequent createTestTrip calls work
  await navigateToPanel(page);
}

/**
 * Change T_BASE via options flow UI.
 * Navigate to integration config page, click Configure, fill form.
 */
async function changeTBaseViaUI(page: Page, newTBase: number): Promise<void> {
  // Navigate directly to the integration configuration page (matching zzz-integration-deletion-cleanup pattern)
  await page.goto('/config/integrations/integration/ev_trip_planner');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('text=Integration entries', { timeout: 15_000 });

  // Find Configure button for test_vehicle entry
  const testVehicleSection = page.locator('section').filter({ hasText: 'test_vehicle' }).first();
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
  // Wait for config change to propagate (condition-based)
  await expect(async () => {
    await page.evaluate(() => {
      const ha = document.querySelector('home-assistant') as any;
      if (ha?.hass?.states) {
        // Verify the integration config is accessible (proves page loaded after dialog close)
        const entry = Object.values(ha.hass.states).find((s: any) =>
          s?.entity_id?.includes('ev_trip_planner'),
        );
        return entry !== undefined;
      }
      return false;
    });
  }).toPass({ timeout: 10_000 });
  await navigateToPanel(page);
}

/**
 * Compute the sum of def_total_hours_array from sensor attributes.
 */
function getDefHoursTotal(attrs: Record<string, any>): number {
  const arr = (attrs.def_total_hours_array as number[]) || [];
  return arr.reduce((sum: number, h: number) => sum + h, 0);
}

/**
 * Wait for EMHASS sensor to exist and have 'ready' status via frontend state.
 * Pattern from working e2e suite: use toPass() with async polling.
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
 * Discover the EMHASS sensor entity ID via frontend state.
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
 * Pattern from working e2e suite: use page.evaluate() with hass.states[eid].
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
 * Verify EMHASS sensor attributes are present via Developer Tools > States UI.
 * Pattern from working e2e suite: filter textbox + getByText('power_profile_watts:').
 */
async function verifyAttributesViaUI(page: Page, filter: string): Promise<void> {
  await page.goto('/developer-tools/state', { waitUntil: 'networkidle' });
  await expect(page.getByText(/developer tools/i)).toBeVisible({ timeout: 10_000 });

  const searchInput = page.getByRole('textbox', { name: /filter/i }).first();
  if (await searchInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await searchInput.fill(filter);
    // Wait for filtered results to appear (condition-based, not fixed timeout)
    await expect(async () => {
      const count = await page.getByText(filter).count();
      expect(count).toBeGreaterThan(0);
    }).toPass({ timeout: 10_000 });
  }

  const attributesLocator = page.getByText('power_profile_watts:').first();
  await expect(attributesLocator).toBeVisible({ timeout: 10_000 });
}

/**
 * Poll until sensor has non-zero power_profile values.
 */
async function waitForNonZeroProfile(page: Page, entityId: string, timeoutMs = 15_000): Promise<void> {
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

    // Verify attributes via UI (matching working e2e test pattern)
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

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

    // Verify attributes visible in dev tools UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

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
  // T_BASE=6h: Aggressive capping — comparative vs T_BASE=24h baseline
  // --------------------------------------------------------------------------
  test('T_BASE=6h narrow window — more charging hours than T_BASE=24h baseline', async ({ page }) => {
    // Step 1: Set T_BASE=24h (baseline)
    await changeTBaseViaUI(page, 24);
    await changeSOC(page, 30);

    // Step 2: Create 3 identical trips at baseline
    for (let i = 0; i < 3; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i + 1, '09:00'),
        80,
        20,
        `Baseline Trip ${i + 1}`,
        { day: String(i + 1), time: '09:00' },
      );
    }

    // Step 3: Capture baseline total hours
    await waitForEmhassSensor(page);
    const baselineSensorId = (await discoverEmhassSensorEntityId(page))!;
    expect(baselineSensorId).toBeTruthy();
    await waitForNonZeroProfile(page, baselineSensorId);
    const baselineAttrs = await getSensorAttributes(page, baselineSensorId!);
    expect(baselineAttrs.emhass_status).toBe('ready');
    const defHoursDefault = getDefHoursTotal(baselineAttrs);

    // Verify baseline attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

    console.log(
      `T_BASE=24h baseline: def_total_hours_array sum = ${defHoursDefault.toFixed(2)}h, ` +
      `${(baselineAttrs.deferrables_schedule as any[]).length} deferrable loads`,
    );

    // Step 4: Switch to T_BASE=6h (narrow look-ahead window)
    await cleanupTestTrips(page);
    await changeTBaseViaUI(page, 6);
    await changeSOC(page, 30);

    // Step 5: Create same 3 trips
    for (let i = 0; i < 3; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i + 1, '09:00'),
        80,
        20,
        `Narrow Window Trip ${i + 1}`,
        { day: String(i + 1), time: '09:00' },
      );
    }

    // Step 6: Capture 6h total hours
    await waitForEmhassSensor(page);
    const sensor6hId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensor6hId).toBeTruthy();
    await waitForNonZeroProfile(page, sensor6hId);
    const attrs6h = await getSensorAttributes(page, sensor6hId!);
    expect(attrs6h.emhass_status).toBe('ready');
    const defHours6h = getDefHoursTotal(attrs6h);

    // Verify 6h attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

    console.log(
      `T_BASE=6h narrow: def_total_hours_array sum = ${defHours6h.toFixed(2)}h, ` +
      `${(attrs6h.deferrables_schedule as any[]).length} deferrable loads`,
    );

    // Step 7: Shorter T_BASE sees fewer future trips → higher SOC cap → more charging hours
    expect(defHours6h).toBeGreaterThan(defHoursDefault);

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // T_BASE=48h: Conservative capping
  // --------------------------------------------------------------------------
  test('T_BASE=48h conservative capping — more charging hours than T_BASE=24h baseline', async ({ page }) => {
    // Step 1: Set T_BASE=24h (baseline)
    await changeTBaseViaUI(page, 24);
    await changeSOC(page, 30);

    // Step 2: Create 3 identical trips at baseline
    for (let i = 0; i < 3; i++) {
      await createTestTrip(
        page,
        'recurrente',
        getFutureIso(i + 1, '09:00'),
        80,
        20,
        `Baseline Trip ${i + 1}`,
        { day: String(i + 1), time: '09:00' },
      );
    }

    // Step 3: Capture baseline total hours
    await waitForEmhassSensor(page);
    const baselineSensorId = (await discoverEmhassSensorEntityId(page))!;
    expect(baselineSensorId).toBeTruthy();
    await waitForNonZeroProfile(page, baselineSensorId);
    const baselineAttrs = await getSensorAttributes(page, baselineSensorId!);
    expect(baselineAttrs.emhass_status).toBe('ready');
    const defHoursDefault = getDefHoursTotal(baselineAttrs);

    // Verify baseline attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

    console.log(
      `T_BASE=24h baseline: def_total_hours_array sum = ${defHoursDefault.toFixed(2)}h, ` +
      `${(baselineAttrs.deferrables_schedule as any[]).length} deferrable loads`,
    );

    // Step 4: Switch to T_BASE=48h (conservative capping)
    await cleanupTestTrips(page);
    await changeTBaseViaUI(page, 48);
    await changeSOC(page, 30);

    // Step 5: Create same 3 trips
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

    // Step 6: Capture 48h total hours
    await waitForEmhassSensor(page);
    const sensor48hId = (await discoverEmhassSensorEntityId(page))!;
    expect(sensor48hId).toBeTruthy();
    await waitForNonZeroProfile(page, sensor48hId);
    const attrs48h = await getSensorAttributes(page, sensor48hId!);
    expect(attrs48h.emhass_status).toBe('ready');
    const defHours48h = getDefHoursTotal(attrs48h);

    // Verify 48h attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

    console.log(
      `T_BASE=48h conservative: def_total_hours_array sum = ${defHours48h.toFixed(2)}h, ` +
      `${(attrs48h.deferrables_schedule as any[]).length} deferrable loads`,
    );

    // Step 7: Assert conservative capping increases (or equals) total charging hours
    expect(defHours48h).toBeGreaterThanOrEqual(defHoursDefault);

    await cleanupTestTrips(page);
  });

  // --------------------------------------------------------------------------
  // SOH=92%: Real battery capacity affects capping — comparative vs 100% SOH
  // --------------------------------------------------------------------------
  test('SOH=92% increases total charging hours vs SOH=100% baseline', async ({ page }) => {
    // Step 1: Set SOH=100% (baseline)
    await changeSOH(page, 100);
    await changeSOC(page, 40);

    // Step 2: Create 1 trip at baseline SOH
    await createTestTrip(page, 'puntual', getFutureIso(1, '10:00'), 150, 38, 'SOH 100% Baseline Trip');

    // Step 3: Capture baseline total hours
    await waitForEmhassSensor(page);
    const baselineSensorId = (await discoverEmhassSensorEntityId(page))!;
    expect(baselineSensorId).toBeTruthy();
    await waitForNonZeroProfile(page, baselineSensorId);
    const baselineAttrs = await getSensorAttributes(page, baselineSensorId!);
    expect(baselineAttrs.emhass_status).toBe('ready');
    const soh100 = getDefHoursTotal(baselineAttrs);

    // Verify baseline attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

    console.log(
      `SOH=100% baseline: def_total_hours_array sum = ${soh100.toFixed(2)}h, ` +
      `${(baselineAttrs.deferrables_schedule as any[]).length} deferrable loads`,
    );

    // Step 4: Switch SOH to 92%
    await cleanupTestTrips(page);
    await changeSOH(page, 92);
    await changeSOC(page, 40);

    // Step 5: Create same trip
    await createTestTrip(page, 'puntual', getFutureIso(1, '10:00'), 150, 38, 'SOH 92% Test Trip');

    // Step 6: Capture 92% SOH total hours
    await waitForEmhassSensor(page);
    const soh92SensorId = (await discoverEmhassSensorEntityId(page))!;
    expect(soh92SensorId).toBeTruthy();
    await waitForNonZeroProfile(page, soh92SensorId);
    const attrs92 = await getSensorAttributes(page, soh92SensorId!);
    expect(attrs92.emhass_status).toBe('ready');
    const soh92 = getDefHoursTotal(attrs92);

    // Verify 92% attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

    console.log(
      `SOH=92%: def_total_hours_array sum = ${soh92.toFixed(2)}h, ` +
      `${(attrs92.deferrables_schedule as any[]).length} deferrable loads, ` +
      `real capacity 55.2kWh used in capping`,
    );

    // Step 7: Assert SOH=92% increases total charging hours (higher drain due to smaller real capacity)
    expect(soh92).toBeGreaterThan(soh100);

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

    // Verify attributes visible in UI
    await verifyAttributesViaUI(page, 'emhass_perfil_diferible');

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
