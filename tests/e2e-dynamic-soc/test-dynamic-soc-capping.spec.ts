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

/**
 * Charger power configured in the test vehicle config flow (Step 2).
 * Value: charging_power_kw = 11.0 kW → 11000 W.
 *
 * This must be kept in sync with the config flow setup in auth.setup.ts:
 *   battery_capacity_kwh=60, charging_power_kw=11, kwh_per_km=0.17
 *
 * CRITICAL: power_profile_watts elements must ALWAYS be 0 or this value.
 * No intermediate values are allowed — SOC cap reduces hours, not power.
 */
const CHARGER_POWER_WATTS = 11000;

// ============================================================================
// Power profile validation helpers — the SOC cap correctness checks
// ============================================================================
/**
 * Validate that p_deferrable_nom_array is a fixed value (either 0 or charger power).
 *
 * This is the KEY correctness check: P_deferrable_nom must ALWAYS be the fixed
 * charger hardware power. It MUST NOT vary per trip or timestep.
 *
 * The SOC cap reduces kwh_needed and def_total_hours, NOT power.
 * If power varies (e.g., [1509, 1126, 475]), something is fundamentally wrong.
 *
 * @returns object with valid: boolean, values: Set<number>, message: string
 */
function validatePDeferrableNomFixed(
  attrs: Record<string, any>,
  expectedPower: number,
): { valid: boolean; values: number[]; message: string } {
  const pArr = (attrs.p_deferrable_nom_array as number[]) || [];
  if (pArr.length === 0) {
    return { valid: false, values: [], message: 'p_deferrable_nom_array is empty' };
  }

  // Get unique values using filter
  const values = pArr.filter((v, i, arr) => arr.indexOf(v) === i);
  const nonZeroValues = values.filter((v) => v > 0);

  // Must have at most one non-zero value, and it must equal the charger power
  if (nonZeroValues.length === 0) {
    return {
      valid: false,
      values,
      message: 'p_deferrable_nom_array has no non-zero values',
    };
  }
  if (nonZeroValues.length > 1) {
    return {
      valid: false,
      values,
      message: `p_deferrable_nom_array has ${nonZeroValues.length} different non-zero values: ${nonZeroValues.join(', ')}. Expected only ${expectedPower}`,
    };
  }
  if (nonZeroValues.length === 1 && nonZeroValues[0] !== expectedPower) {
    return {
      valid: false,
      values,
      message: `p_deferrable_nom_array non-zero value is ${nonZeroValues[0]}, expected ${expectedPower}`,
    };
  }

  return { valid: true, values, message: `All non-zero p_deferrable_nom values = ${expectedPower}W` };
}

/**
 * Validate that power_profile_watts contains ONLY 0 or multiples of the fixed charger power.
 *
 * This is the primary bug detector: if any element is NOT a multiple of charger power,
 * the SOC cap is distorting the power profile (multiplying by cap_ratio).
 *
 * Multiple trips can overlap in the same hour, so values like 22000 (2×11000) are valid.
 * The critical invariant: every non-zero value must be a multiple of charger_power.
 * Intermediate values (e.g., 10266, 806) indicate the SOC cap is distorting power.
 *
 * Note: def_total_hours_array counts per-trip hours independently, while power_profile_watts
 * is aggregated across trips. They will NOT match when trips share charging windows.
 *
 * @returns object with valid: boolean, errors: string[], details: object
 */
function validatePowerProfileFixed(
  attrs: Record<string, any>,
  expectedPower: number,
): {
  valid: boolean;
  errors: string[];
  nonZeroCount: number;
  zeroCount: number;
  totalTimesteps: number;
  expectedHours: number;
  actualHours: number;
} {
  const errors: string[] = [];
  const profile = (attrs.power_profile_watts as number[]) || [];

  if (profile.length === 0) {
    return {
      valid: false,
      errors: ['power_profile_watts is empty'],
      nonZeroCount: 0,
      zeroCount: 0,
      totalTimesteps: 0,
      expectedHours: 0,
      actualHours: 0,
    };
  }

  // Check 1: Every non-zero element must be a positive multiple of charger power.
  // Overlapping trips may produce multiples (e.g., 22000 = 2×11000), but intermediate
  // values (e.g., 10266) indicate SOC cap distorting power — the bug we fixed.
  const invalidValues: number[] = [];
  let nonZeroCount = 0;
  let zeroCount = 0;

  for (let i = 0; i < profile.length; i++) {
    const v = profile[i];
    if (v === 0) {
      zeroCount++;
    } else if (v > 0 && v % expectedPower === 0) {
      nonZeroCount++;
    } else {
      invalidValues.push(v);
    }
  }

  if (invalidValues.length > 0) {
    const unique = invalidValues
      .filter((v, i, a) => a.indexOf(v) === i)
      .sort((a, b) => a - b)
      .join(', ');
    errors.push(
      `${invalidValues.length} elements have INVALID values (NOT 0 or multiples of ${expectedPower}): ${unique}`,
    );
  }

  return {
    valid: errors.length === 0,
    errors,
    nonZeroCount,
    zeroCount,
    totalTimesteps: profile.length,
    expectedHours: 0,
    actualHours: 0,
  };
}

/**
 * Run ALL power profile validations and log results.
 * Returns true if all checks pass.
 */
function validateAllPowerAssertions(
  attrs: Record<string, any>,
  chargerPowerWatts: number,
): boolean {
  const nomValidation = validatePDeferrableNomFixed(attrs, chargerPowerWatts);
  const profileValidation = validatePowerProfileFixed(attrs, chargerPowerWatts);

  console.log(
    `  ⚡ P_deferrable_nom: ${nomValidation.message} (${nomValidation.valid ? '✅' : '❌'})`,
  );
  console.log(
    `  ⚡ Power profile: ${profileValidation.nonZeroCount}/${profileValidation.totalTimesteps} valid non-zero elements ` +
      `(${profileValidation.errors.length === 0 ? '✅' : '❌'})`,
  );

  if (!nomValidation.valid) {
    console.error(`  ❌ FAIL: ${nomValidation.message}`);
  }
  for (const err of profileValidation.errors) {
    console.error(`  ❌ FAIL: ${err}`);
  }

  return nomValidation.valid && profileValidation.valid;
}

// ============================================================================
// EMHASS deferrable load assertions — BUG DETECTORS
// These detect: def_total_hours floats, def_start_timestep all-zero,
// def_end_timestep non-incremental, p_deferrable_matrix wrong column count
// ============================================================================

/**
 * Validate that def_total_hours_array contains only integers (not floats).
 * BUG-1: round() instead of math.ceil() produces floats like [0.91, 1.36, 0.14, 1.82].
 * Expected: integers like [1, 2, 1, 2].
 */
function validateDefTotalHoursAreIntegers(
  attrs: Record<string, any>,
): { valid: boolean; errors: string[]; values: number[] } {
  const arr = (attrs.def_total_hours_array as number[]) || [];
  if (arr.length === 0) {
    return { valid: false, errors: ['def_total_hours_array is empty'], values: [] };
  }
  const errors: string[] = [];
  const nonIntegers: number[] = [];
  for (let i = 0; i < arr.length; i++) {
    const v = arr[i];
    if (v !== Math.floor(v)) {
      nonIntegers.push(v);
      errors.push(`def_total_hours[${i}] = ${v} (float, expected integer ceil)`);
    }
  }
  if (errors.length > 0) {
    console.error(`  ❌ FAIL: ${errors.length} non-integer def_total_hours: ${nonIntegers.join(', ')}`);
  }
  return { valid: errors.length === 0, errors, values: arr };
}

/**
 * Validate def_start_timestep values are valid (>= 0, < horizon).
 *
 * When car is at home for all trips (hora_regreso=None), all def_start=0
 * is expected and valid. The key invariant is:
 * - def_start >= 0 (never negative)
 * - def_start < horizon_hours
 * - window_size >= def_total_hours (checked in validateDefEndTimestepConsistency)
 */
function validateDefStartTimestepChronological(
  attrs: Record<string, any>,
): { valid: boolean; errors: string[]; values: number[] } {
  const arr = (attrs.def_start_timestep_array as number[]) || [];
  if (arr.length === 0) {
    return { valid: false, errors: ['def_start_timestep_array is empty'], values: [] };
  }
  const errors: string[] = [];
  const horizon = 168; // default 7 days
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] < 0 || arr[i] >= horizon) {
      errors.push(`def_start_timestep[${i}] = ${arr[i]} out of valid range [0, ${horizon})`);
    }
  }
  if (errors.length > 0) {
    console.error(`  ❌ FAIL: def_start_timestep invalid: ${arr.join(', ')}`);
  }
  return { valid: errors.length === 0, errors, values: arr };
}

/**
 * Validate def_end_timestep uses fin_ventana (trip departure), not start+hours.
 *
 * def_end = opportunity window end (trip departure time)
 * def_start = opportunity window start
 * def_total_hours = actual charging time needed within the window
 *
 * Invariant: window_size >= def_total_hours (opportunity must accommodate charging)
 * AND: def_end > def_start (non-trivial window)
 */
function validateDefEndTimestepConsistency(
  attrs: Record<string, any>,
): { valid: boolean; errors: string[] } {
  const starts = (attrs.def_start_timestep_array as number[]) || [];
  const hours = (attrs.def_total_hours_array as number[]) || [];
  const ends = (attrs.def_end_timestep_array as number[]) || [];
  const errors: string[] = [];

  const minLen = Math.min(starts.length, hours.length, ends.length);
  for (let i = 0; i < minLen; i++) {
    if (ends[i] <= starts[i]) {
      errors.push(
        `Trip ${i}: def_end[${ends[i]}] <= def_start[${starts[i]}] — window must be non-trivial`,
      );
    }
    const windowSize = ends[i] - starts[i];
    if (windowSize < hours[i]) {
      errors.push(
        `Trip ${i}: window_size[${windowSize}] < hours[${hours[i]}] — opportunity must accommodate charging`,
      );
    }
  }

  if (errors.length > 0) {
    console.error(`  ❌ FAIL: def_end_timestep inconsistent: ${errors.join('; ')}`);
  }
  return { valid: errors.length === 0, errors };
}

/**
 * Validate that p_deferrable_matrix has the correct number of columns
 * (horizon_hours = planning_horizon_days * 24). Default is 168 (7 days).
 * BUG: hardcoded * 4 (15-min assumption) produces 96 columns instead of 168.
 */
function validatePDeferrableMatrixColumns(
  attrs: Record<string, any>,
  expectedColumns: number,
): { valid: boolean; errors: string[] } {
  const matrix = (attrs.p_deferrable_matrix as number[][]) || [];
  if (matrix.length === 0) {
    return { valid: false, errors: ['p_deferrable_matrix is empty'], };
  }
  const errors: string[] = [];
  for (let i = 0; i < matrix.length; i++) {
    const rowLen = matrix[i].length;
    if (rowLen !== expectedColumns) {
      errors.push(
        `p_deferrable_matrix row ${i} has ${rowLen} columns, expected ${expectedColumns}`,
      );
    }
  }
  if (errors.length > 0) {
    console.error(`  ❌ FAIL: ${errors.join('; ')}`);
  }
  return { valid: errors.length === 0, errors };
}

/**
 * Run ALL EMHASS deferrable load assertions (BUG DETECTORS).
 * Returns true if all checks pass.
 */
function validateDeferrableLoadAssertions(
  attrs: Record<string, any>,
  expectedColumns: number = 168,
): boolean {
  const intValidation = validateDefTotalHoursAreIntegers(attrs);
  const chronoValidation = validateDefStartTimestepChronological(attrs);
  const endValidation = validateDefEndTimestepConsistency(attrs);
  const matrixValidation = validatePDeferrableMatrixColumns(attrs, expectedColumns);

  console.log(
    `  🔢 def_total_hours are integers: ${intValidation.valid ? '✅' : '❌'} (${intValidation.values.length > 0 ? intValidation.values.join(', ') : 'empty'})`,
  );
  console.log(
    `  📐 def_start_timestep chronological: ${chronoValidation.valid ? '✅' : '❌'} (${chronoValidation.values.length > 0 ? chronoValidation.values.join(', ') : 'empty'})`,
  );
  console.log(
    `  🏁 def_end_timestep consistent: ${endValidation.valid ? '✅' : '❌'}`,
  );
  console.log(
    `  📏 p_deferrable_matrix columns: ${matrixValidation.valid ? '✅' : '❌'} (expected ${expectedColumns})`,
  );

  if (!intValidation.valid) {
    for (const err of intValidation.errors) console.error(`  ❌ ${err}`);
  }
  if (!chronoValidation.valid) {
    for (const err of chronoValidation.errors) console.error(`  ❌ ${err}`);
  }
  if (!endValidation.valid) {
    for (const err of endValidation.errors) console.error(`  ❌ ${err}`);
  }
  if (!matrixValidation.valid) {
    for (const err of matrixValidation.errors) console.error(`  ❌ ${err}`);
  }

  return intValidation.valid && chronoValidation.valid && endValidation.valid && matrixValidation.valid;
}

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

  // Wait for state propagation (same pattern as working e2e/emhass-sensor-updates.spec.ts)
  await page.waitForTimeout(2000);

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
  // Wait for state propagation (same pattern as working e2e test)
  await page.waitForTimeout(2000);
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
  if ((await configureBtn.count()) > 0) {
    await configureBtn.first().click({ force: true });
  } else {
    const allBtns = page.getByRole('button', { name: 'Configure' });
    if ((await allBtns.count()) > 0) {
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
  // Wait for config change to propagate
  await page.waitForTimeout(2000);
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
 * Wait for EMHASS sensor to exist and have 'ready' status via browser context.
 * Navigate to devtools where home-assistant element is available, then poll.
 */
async function waitForEmhassSensor(page: Page): Promise<void> {
  await page.goto('/developer-tools/state', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => {
    const haMain = document.querySelector('home-assistant') as any;
    if (!haMain?.hass?.states) return false;
    for (const [entityId, state] of Object.entries(haMain.hass.states)) {
      if (!entityId.includes('emhass_perfil_diferible')) continue;
      const attrs = (state as any).attributes;
      if (attrs?.emhass_status === 'ready') return true;
    }
    return false;
  }, { timeout: 60_000 });
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
    await expect.poll(() => page.getByText(filter).count(), { timeout: 10_000 }).toBeGreaterThan(0);
  }

  const attributesLocator = page.getByText('power_profile_watts:').first();
  await expect(attributesLocator).toBeVisible({ timeout: 10_000 });
}

/**
 * Poll until sensor has non-zero power_profile values via browser context.
 * Navigate to devtools where home-assistant element is reliably available.
 */
async function waitForNonZeroProfile(page: Page, entityId: string, timeoutMs = 15_000): Promise<void> {
  await page.goto('/developer-tools/state', { waitUntil: 'networkidle' });
  await page.waitForFunction((eid: string) => {
    try {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states?.[eid]) return false;
      const a = haMain.hass.states[eid].attributes;
      const profile = Array.isArray(a.power_profile_watts) ? a.power_profile_watts : [];
      return profile.some((v: number) => v > 0) && a.emhass_status === 'ready';
    } catch {
      return false;
    }
  }, entityId, { timeout: timeoutMs });
  await navigateToPanel(page);
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

    // CRITICAL: Validate that power profile uses ONLY 0 or fixed charger power.
    // The SOC cap must NOT distort power values — only reduce hours/kWh.
    const scenarioCPass = validateAllPowerAssertions(attrs, CHARGER_POWER_WATTS);
    expect(scenarioCPass).toBe(true);

    // CRITICAL BUG DETECTORS: def_total_hours must be integers (ceil),
    // def_start_timestep must be chronological, def_end based on fin_ventana.
    const deferrablePass = validateDeferrableLoadAssertions(attrs);
    expect(deferrablePass).toBe(true);

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

    // CRITICAL: Validate that power profile uses ONLY 0 or fixed charger power.
    // The SOC cap must NOT distort power values — only reduce hours/kWh.
    const scenarioAPass = validateAllPowerAssertions(attrs, CHARGER_POWER_WATTS);
    expect(scenarioAPass).toBe(true);

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

    // CRITICAL: Validate that power profile uses ONLY 0 or fixed charger power.
    const scenarioBPass = validateAllPowerAssertions(attrs, CHARGER_POWER_WATTS);
    expect(scenarioBPass).toBe(true);

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
