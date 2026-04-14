/**
 * E2E Test: Panel.js EMHASS Sensor Entity ID Match
 *
 * BUG #3/#4: Panel.js uses incorrect entity ID pattern for EMHASS sensor.
 *
 * PROBLEM:
 * - panel.js line 877 uses: `sensor.ev_trip_planner_${lowerVehicleId}_emhass_aggregated`
 * - Actual sensor entity ID (emhass_adapter.py:844): `sensor.emhass_perfil_diferible_{entry_id}`
 *
 * RESULT: Panel never finds the sensor, shows "Sensor Unavailable", copy button is disabled.
 *
 * This test verifies:
 * 1. The sensor exists with the correct entity ID pattern (emhass_perfil_diferible_{entry_id})
 * 2. After creating a trip, the sensor is available and populated
 */

import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, cleanupTestTrips, createTestTrip } from './trips-helpers';

test.describe('Panel EMHASS Sensor Entity ID Match', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('EMHASS sensor exists with correct entity ID pattern after trip creation', async ({
    page,
  }) => {
    // Step 1: Create a trip to trigger EMHASS recalculation
    await createTestTrip(
      page,
      'puntual',
      '2026-04-20T10:00',
      30,
      12,
      'E2E Entity ID Test Trip',
    );

    // Step 2: Wait for EMHASS recalculation (NFR-1: up to 2 seconds)
    await page.waitForTimeout(3000);

    // Step 3: Navigate to Developer Tools > States
    await page.goto('/developer-tools/state');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Step 4: Wait for the states page to load
    await expect(
      page.getByText(/developer tools/i),
    ).toBeVisible({ timeout: 10000 });

    // Step 5: Find the filter/search input
    const searchInput = page.getByRole('textbox', { name: /filter/i }).first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('emhass_perfil_diferible');
      await page.waitForTimeout(1000);
    }

    // Step 6: Verify sensor exists with CORRECT entity ID pattern
    // CORRECT pattern: sensor.emhass_perfil_diferible_{entry_id}
    // WRONG pattern (bug): sensor.ev_trip_planner_{vehicleId}_emhass_aggregated
    const sensorRow = page.getByText(/emhass_perfil_diferible/i).first();
    await expect(sensorRow).toBeVisible({ timeout: 10000 });

    // Step 7: Get the full text content of the sensor row
    const rowText = await sensorRow.textContent();
    console.log('Found EMHASS sensor row:', rowText);

    // The sensor should exist and have a state (not empty)
    expect(rowText).toBeDefined();
    expect(rowText?.length).toBeGreaterThan(0);

    // BUG #3/#4 note:
    // The panel.js code currently uses the WRONG entity ID pattern:
    // `sensor.ev_trip_planner_${lowerVehicleId}_emhass_aggregated`
    //
    // This is why the panel shows "Sensor Unavailable" even when the sensor exists.
    // The panel is looking for the wrong entity!
    //
    // The correct entity ID is: sensor.emhass_perfil_diferible_{entry_id}
    // (e.g., sensor.emhass_perfil_diferible_test_vehicle)
  });

  test('EMHASS sensor state is available after trip creation', async ({ page }) => {
    // Step 1: Create a trip
    await createTestTrip(
      page,
      'puntual',
      '2026-04-20T10:00',
      30,
      12,
      'E2E EMHASS State Test Trip',
    );

    // Step 2: Wait for EMHASS recalculation
    await page.waitForTimeout(3000);

    // Step 3: Navigate to Developer Tools > States
    await page.goto('/developer-tools/state');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Step 4: Find the EMHASS sensor
    const searchInput = page.getByRole('textbox', { name: /filter/i }).first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('emhass_perfil_diferible');
      await page.waitForTimeout(1000);
    }

    const sensorRow = page.getByText(/emhass_perfil_diferible/i).first();
    await expect(sensorRow).toBeVisible({ timeout: 10000 });

    // Step 5: Get the full text content
    const rowText = (await sensorRow.textContent()) ?? '';
    console.log('EMHASS sensor state row:', rowText);

    // The sensor should have a state value (ready, active, error, etc.)
    // NOT empty
    expect(rowText.length).toBeGreaterThan(0);

    // Verify sensor is not unavailable or unknown
    const lowerText = rowText.toLowerCase();
    expect(lowerText).not.toContain('unavailable');
    expect(lowerText).not.toContain('unknown');
  });
});
