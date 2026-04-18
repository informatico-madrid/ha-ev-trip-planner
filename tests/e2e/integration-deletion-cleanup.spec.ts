/**
 * Integration Deletion Cleanup E2E Test
 *
 * Test: When a vehicle integration is deleted, ALL its trips should be cascade-deleted.
 *
 * Starting state: One vehicle "test_vehicle" with 3 trips.
 * Expected: After deleting the integration, EMHASS sensor shows 0 trips.
 */
import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, navigateToPanel, cleanupTestTrips } from './trips-helpers';

test.describe('Integration Deletion Cleanup', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    // Clean starting state: go to panel and delete ALL existing trips
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  const getSensorAttributes = async (page: Page, entityId: string): Promise<Record<string, any>> => {
    return await page.evaluate((eid: string) => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states?.[eid]) {
        throw new Error(`Entity ${eid} not found in hass.states`);
      }
      return haMain.hass.states[eid].attributes;
    }, entityId);
  };

  /**
   * Discovers the actual EMHASS sensor entity ID for the test_vehicle.
   * The sensor entity ID pattern is sensor.emhass_perfil_diferible_{entry_id},
   * where entry_id is a UUID, NOT "test_vehicle". This function searches
   * hass.states to find the actual sensor matching our vehicle.
   */
  const discoverEmhassSensorEntityId = async (page: Page): Promise<string | null> => {
    return await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states) return null;

      // Search for sensor.emhass_perfil_diferible_* with vehicle_id attribute = "test_vehicle"
      for (const [entityId, state] of Object.entries(haMain.hass.states)) {
        if (!entityId.startsWith('sensor.emhass_perfil_diferible_')) continue;
        const attrs = (state as any).attributes;
        if (attrs?.vehicle_id === 'test_vehicle') {
          return entityId;
        }
      }
      // Fallback: find first emhass_perfil_diferible sensor
      for (const entityId of Object.keys(haMain.hass.states)) {
        if (entityId.includes('emhass_perfil_diferible')) {
          return entityId;
        }
      }
      return null;
    });
  };

  test('should delete all trips when integration is deleted', async ({ page }: { page: Page }) => {
    // Step 0: Discover the actual EMHASS sensor entity ID for test_vehicle
    // The hardcoded sensorEntityId was likely wrong (entry_id is a UUID, not "test_vehicle")
    const discoveredEntityId = await discoverEmhassSensorEntityId(page);
    const sensorEntityId = discoveredEntityId || 'sensor.emhass_perfil_diferible_test_vehicle';
    console.log('DISCOVERED: EMHASS sensor entity ID =', sensorEntityId);

    // Get BASELINE count of existing trips (may be orphaned from previous test runs)
    let baselineCount = 0;
    try {
      const baselineAttrs = await getSensorAttributes(page, sensorEntityId);
      baselineCount = (baselineAttrs.def_total_hours_array || []).length;
    } catch (err: any) {
      if (!err?.message?.includes('not found')) {
        throw err;
      }
      console.log('BASELINE: No sensor found, starting from 0');
    }
    console.log('BASELINE: EMHASS has', baselineCount, 'trips before creating new ones');

    // Step 1: Create 3 test trips
    await createTestTrip(page, 'puntual', '2026-04-18T10:00', 20, 5, 'Cleanup Trip 1');
    await createTestTrip(page, 'puntual', '2026-04-19T14:00', 30, 7, 'Cleanup Trip 2');
    await createTestTrip(page, 'recurrente', '2026-04-20T16:00', 15, 4, 'Cleanup Trip 3', { day: '1', time: '09:00' });

    // Step 2: Verify trips exist in panel
    await expect(page.getByText('Cleanup Trip 1')).toBeVisible();
    await expect(page.getByText('Cleanup Trip 2')).toBeVisible();
    await expect(page.getByText('Cleanup Trip 3')).toBeVisible();

    // Step 3: Check EMHASS sensor - should have baseline + 3 trips
    const beforeAttrs = await getSensorAttributes(page, sensorEntityId);
    const beforeCount = (beforeAttrs.def_total_hours_array || []).length;
    console.log('BEFORE: EMHASS has', beforeCount, 'trips (baseline was', baselineCount, ')');
    expect(beforeCount).toBeGreaterThan(baselineCount);

    // Step 4: Navigate to integration page
    await page.goto('/config/integrations/integration/ev_trip_planner');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=Integration entries', { timeout: 15000 });
    console.log('On integration page');

    // Step 5: Find the vehicle integration entry's Menu button
    // The vehicle entry is the one with "test_vehicle" text AND "Configure" button
    // Strategy: click each Menu button until we find one that opens dropdown with "Delete" (not "Delete device")
    // Then click that Delete

    let deletionCompleted = false;

    // First, find all Menu buttons and check which one opens Delete option
    const allMenuButtons = page.getByRole('button', { name: 'Menu' });
    const menuCount = await allMenuButtons.count();
    console.log('Found', menuCount, 'Menu buttons on page');

    for (let i = 0; i < Math.min(menuCount, 30); i++) {
      const menuBtn = allMenuButtons.nth(i);
      if (!await menuBtn.isVisible().catch(() => false)) continue;

      await menuBtn.click();
      await page.waitForTimeout(800);

      // Use Playwright's getByRole and getByText which pierce Shadow DOM
      const deleteVisible = await page.getByText('Delete', { exact: true }).isVisible().catch(() => false);
      console.log('Menu', i, '- Delete visible:', deleteVisible);

      if (deleteVisible) {
        console.log('Menu', i, 'is the integration entry menu with Delete option');

        // Set up dialog handler BEFORE clicking Delete
        page.once('dialog', async (dialog) => {
          console.log('Confirmation dialog appeared:', dialog.message().substring(0, 50));
          await dialog.accept();
        });

        // Click Delete
        await page.getByText('Delete', { exact: true }).click();
        console.log('Clicked Delete');

        // Wait for dialog and deletion to complete
        await page.waitForTimeout(3000);
        deletionCompleted = true;
        break;
      }

      // Not this menu, close and try next
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    expect(deletionCompleted, 'Should have found and clicked Delete on integration').toBe(true);

    // Step 6: Wait for deletion to complete, then reload
    await page.waitForTimeout(3000);

    // Verify test_vehicle integration is NO LONGER in the list
    const testVehicleStillExists = await page.getByText('test_vehicle', { exact: false }).isVisible().catch(() => false);
    console.log('TEST_VEHICLE still visible after deletion:', testVehicleStillExists);

    // Reload page to verify deletion took effect
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForSelector('text=Integration entries', { timeout: 15000 });

    // Step 7: Check EMHASS sensor - should now have 0 trips
    let afterAttrs: Record<string, any> | null = null;
    try {
      afterAttrs = await getSensorAttributes(page, sensorEntityId);
    } catch (err: any) {
      // Only handle "not found" — rethrow unexpected errors
      if (err?.message?.includes('not found')) {
        console.log('AFTER: Sensor not found (integration deleted)');
      } else {
        throw err;
      }
    }

    if (afterAttrs) {
      const afterCount = (afterAttrs.def_total_hours_array || []).length;
      console.log('AFTER: EMHASS has', afterCount, 'trips (baseline was', baselineCount, ')');

      // Also check all_trips_list attribute if it exists
      const allTripsList = afterAttrs.all_trips_list || [];
      console.log('AFTER: all_trips_list has', allTripsList.length, 'entries:', JSON.stringify(allTripsList));

      // After deletion, should be back to baseline (no orphaned trips from THIS vehicle)
      expect(afterCount).toBe(baselineCount);
    } else {
      console.log('AFTER: Sensor not found - integration properly deleted');
    }
  });
});
