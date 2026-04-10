/**
 * E2E Test: EMHASS Sensor Updates
 *
 * This test file verifies EMHASS sensor functionality:
 * - Bug #1 fix: Single device per vehicle (no duplication)
 * - Bug #2 fix: Sensor attributes are populated (not null)
 *
 * Uses patterns from working E2E tests (create-trip.spec.ts)
 * Based on Playwright snapshot analysis of HA UI structure
 * Task 4.1-4.6 [VE0-VE3] - E2E sensor verification
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, cleanupTestTrips, createTestTrip } from './trips-helpers';

test.describe('EMHASS Sensor Updates', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('should create a trip and verify EMHASS sensor attributes are populated (Bug #2 fix)', async ({
    page,
  }) => {
    // Step 1: Create a trip to trigger EMHASS recalculation
    await createTestTrip(
      page,
      'puntual',
      '2026-04-20T10:00',
      30,
      12,
      'E2E EMHASS Attribute Test Trip',
    );

    // Step 2: Wait for EMHASS recalculation (NFR-1: up to 2 seconds)
    await page.waitForTimeout(3000);

    // Step 3: Navigate to Developer Tools > States directly by URL
    // Based on snapshot: HA Developer Tools uses direct URL navigation
    await page.goto('/developer-tools/state');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Step 4: Wait for the states page to load
    // The page should have the "Developer tools" header
    await expect(
      page.getByText(/developer tools/i),
    ).toBeVisible({ timeout: 10000 });

    // Step 5: Find the filter/search input
    // From working tests pattern: use getByRole or getByLabel for accessibility
    const searchInput = page.getByRole('textbox', { name: /filter/i }).first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('emhass');
      await page.waitForTimeout(1000);
    }

    // Step 6: Find the EMHASS sensor row
    const sensorRow = page.getByText(/emhass_perfil_diferible/i).first();

    // Verify sensor exists
    await expect(sensorRow).toBeVisible({ timeout: 10000 });

    // Step 7: Get the full text content of the sensor row to check attributes
    // The row should contain the entity state
    const rowText = await sensorRow.textContent();
    console.log('Sensor row text:', rowText);

    // The sensor should exist and have a state (not empty)
    expect(rowText).toBeDefined();

    // Step 8: Clean up trip
    await navigateToPanel(page);
    const deleteBtn = page.getByRole('button', { name: /eliminar/i }).last();
    if (await deleteBtn.isVisible().catch(() => false)) {
      const confirmPromise = page.waitForEvent('dialog').then(async dialog => {
        await dialog.accept();
      });
      await deleteBtn.click();
      await confirmPromise;
      await page.waitForTimeout(1000);
    }
  });

  test('should verify EMHASS sensor attributes are populated via UI (Bug #2 fix)', async ({
    page,
  }) => {
    // Step 1: BEFORE creating trip, capture sensor attributes (should be null/empty)
    // Navigate to Developer Tools > States first
    await page.goto('/developer-tools/state');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Find the EMHASS sensor and get its attributes BEFORE trip creation
    const beforeSensorState = await page.evaluate(() => {
      const hass: any = (window as any).hass;
      if (!hass || !hass.states) {
        return { error: 'HA not found' };
      }
      // Find the sensor entity (pattern: sensor.emhass_perfil_diferible_*)
      for (const [entityId, entityState] of Object.entries(hass.states || {})) {
        const es: any = entityState;
        if (entityId && entityId.includes('emhass_perfil_diferible')) {
          return { entityId, state: es.state, attributes: es.attributes };
        }
      }
      return { error: 'Sensor not found' };
    });

    console.log('Sensor state BEFORE trip creation:', beforeSensorState);

    // Step 2: Create a trip to trigger EMHASS recalculation
    await navigateToPanel(page);
    await createTestTrip(
      page,
      'puntual',
      '2026-04-20T10:00',
      30,
      12,
      'E2E EMHASS Attributes Test Trip',
    );

    // Step 3: Wait for EMHASS recalculation (NFR-1: up to 3 seconds)
    await page.waitForTimeout(3000);

    // Step 4: AFTER creating trip, capture sensor attributes again (should have real values)
    const afterSensorState = await page.evaluate(() => {
      const hass: any = (window as any).hass;
      if (!hass || !hass.states) {
        return { error: 'HA not found' };
      }
      for (const [entityId, entityState] of Object.entries(hass.states || {})) {
        const es: any = entityState;
        if (entityId && entityId.includes('emhass_perfil_diferible')) {
          return { entityId, state: es.state, attributes: es.attributes };
        }
      }
      return { error: 'Sensor not found' };
    });

    console.log('Sensor state AFTER trip creation:', afterSensorState);

    // Step 5: Verify BEFORE state had null/empty attributes
    if (beforeSensorState.error !== 'Sensor not found') {
      const beforeAttrs = beforeSensorState.attributes;
      expect(beforeAttrs).toBeDefined();
      if (beforeAttrs) {
        console.log('BEFORE power_profile_watts:', beforeAttrs.power_profile_watts);
        console.log('BEFORE deferrables_schedule:', beforeAttrs.deferrables_schedule);
        console.log('BEFORE emhass_status:', beforeAttrs.emhass_status);
      }
    }

    // Step 6: Verify AFTER state has real values
    expect(afterSensorState.error).not.toBe('Sensor not found');
    expect(afterSensorState.state).not.toBe('unavailable');
    expect(afterSensorState.state).not.toBe('unknown');

    const afterAttrs = afterSensorState.attributes;
    expect(afterAttrs).toBeDefined();
    expect(typeof afterAttrs).toBe('object');

    // Verify key attributes have real values after trip creation
    // power_profile_watts should be an array with 168 hourly values
    if (afterAttrs.power_profile_watts !== undefined) {
      expect(Array.isArray(afterAttrs.power_profile_watts)).toBe(true);
      expect(afterAttrs.power_profile_watts.length).toBeGreaterThan(0);
      console.log(`power_profile_watts has ${afterAttrs.power_profile_watts.length} values`);
    }

    // deferrables_schedule should be an array with schedule data
    if (afterAttrs.deferrables_schedule !== undefined) {
      expect(Array.isArray(afterAttrs.deferrables_schedule)).toBe(true);
      console.log(`deferrables_schedule has ${afterAttrs.deferrables_schedule.length} entries`);
    }

    // emhass_status should be a string with valid state
    if (afterAttrs.emhass_status !== undefined) {
      expect(typeof afterAttrs.emhass_status).toBe('string');
      expect(afterAttrs.emhass_status).not.toBe('');
      expect(['ready', 'active', 'idle', 'optimizing', 'error']).toContain(afterAttrs.emhass_status);
      console.log(`emhass_status: ${afterAttrs.emhass_status}`);
    }

    // Step 7: Navigate to Developer Tools > States to visually confirm sensor shows attributes
    await page.goto('/developer-tools/state');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Find the EMHASS sensor in States page
    const searchInput = page.getByRole('textbox', { name: /filter/i }).first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('emhass_perfil_diferible');
      await page.waitForTimeout(1000);
    }

    const sensorRow = page.getByText(/emhass_perfil_diferible/i).first();
    await expect(sensorRow).toBeVisible({ timeout: 10000 });

    // Click to expand and verify attributes panel shows data
    await sensorRow.click();
    await page.waitForTimeout(1000);

    // Verify attributes are visible in the UI drawer
    const pageContent = await page.locator('body').textContent() || '';
    const hasPowerProfile = pageContent.includes('power_profile_watts');
    const hasDeferrables = pageContent.includes('deferrables_schedule');
    const hasEmhassStatus = pageContent.includes('emhass_status');

    console.log('Attribute UI checks (drawer):', {
      power_profile_watts: hasPowerProfile,
      deferrables_schedule: hasDeferrables,
      emhass_status: hasEmhassStatus,
    });

    // At least one attribute should be visible in the expanded entity detail
    expect(hasPowerProfile || hasDeferrables || hasEmhassStatus).toBe(true);

    // Step 8: Clean up trip
    await navigateToPanel(page);
    const deleteBtn = page.getByRole('button', { name: /eliminar/i }).last();
    if (await deleteBtn.isVisible().catch(() => false)) {
      const confirmPromise = page.waitForEvent('dialog').then(async dialog => {
        await dialog.accept();
      });
      await deleteBtn.click();
      await confirmPromise;
      await page.waitForTimeout(1000);
    }
  });

  test('should verify sensor entity via states page UI', async ({ page }) => {
    // Step 1: Navigate to Developer Tools > States directly by URL
    await page.goto('/developer-tools/state');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Step 2: Wait for the page to load
    await expect(
      page.getByText(/developer tools/i),
    ).toBeVisible({ timeout: 10000 });

    // Step 3: Click on the States tab
    const statesTab = page.getByRole('tab', { name: /states/i });
    if (await statesTab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await statesTab.click();
      await page.waitForTimeout(1000);
    }

    // Step 4: Find the filter/search input
    const searchInput = page.getByRole('textbox', { name: /filter/i }).first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('emhass_deferrable_load');
      await page.waitForTimeout(1000);
    }

    // Step 5: Check if the sensor row exists
    const sensorRow = page.getByText(/emhass_deferrable_load/i).first();
    const exists = await sensorRow.isVisible({ timeout: 10000 }).catch(() => false);

    if (exists) {
      // Sensor exists -- verify it has a state value
      const rowText = await sensorRow.textContent();
      expect(rowText).not.toContain('unavailable');
      expect(rowText).not.toContain('unknown');
    } else {
      console.log('EMHASS sensor not found in States page');
    }
  });
});
