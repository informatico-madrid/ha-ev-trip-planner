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

  const discoverEmhassSensorEntityId = async (page: Page): Promise<string | null> => {
    return await page.evaluate(() => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass?.states) return null;
      for (const [entityId, state] of Object.entries(haMain.hass.states)) {
        if (!entityId.startsWith('sensor.emhass_perfil_diferible_')) continue;
        const attrs = (state as any).attributes;
        if (attrs?.vehicle_id === 'test_vehicle') return entityId;
      }
      for (const entityId of Object.keys(haMain.hass.states)) {
        if (entityId.includes('emhass_perfil_diferible')) return entityId;
      }
      return null;
    });
  };

  const getFutureIso = (daysOffset: number, timeStr: string = '08:00'): string => {
    const pad = (n: number) => String(n).padStart(2, '0');
    const d = new Date();
    d.setDate(d.getDate() + daysOffset);
    const [hh, mm] = (timeStr || '08:00').split(':').map((s) => Number(s));
    d.setHours(hh, mm, 0, 0);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
      d.getHours(),
    )}:${pad(d.getMinutes())}`;
  };

  test('should delete all trips when integration is deleted', async ({ page }: { page: Page }) => {
    const discoveredEntityId = await discoverEmhassSensorEntityId(page);
    const sensorEntityId = discoveredEntityId || 'sensor.emhass_perfil_diferible_test_vehicle';

    // Get baseline trip count
    let baselineCount = 0;
    try {
      const baselineAttrs = await getSensorAttributes(page, sensorEntityId);
      baselineCount = (baselineAttrs.def_total_hours_array || []).length;
    } catch (err: any) {
      if (!err?.message?.includes('not found')) throw err;
    }

    // Create 3 test trips with computed future datetimes to avoid flakiness
    await createTestTrip(page, 'puntual', getFutureIso(1, '10:00'), 20, 5, 'Cleanup Trip 1');
    await createTestTrip(page, 'puntual', getFutureIso(2, '14:00'), 30, 7, 'Cleanup Trip 2');
    await createTestTrip(page, 'recurrente', getFutureIso(3, '16:00'), 15, 4, 'Cleanup Trip 3', { day: '1', time: '09:00' });

    await expect(page.getByText('Cleanup Trip 1')).toBeVisible();
    await expect(page.getByText('Cleanup Trip 2')).toBeVisible();
    await expect(page.getByText('Cleanup Trip 3')).toBeVisible();

    // Re-discover EMHASS sensor after creating trips to ensure we use the actual sensor
    // This handles the case where initial discovery might fallback to vehicle-id based id
    const discoveredAgain = await discoverEmhassSensorEntityId(page);
    const activeSensorEntityId = discoveredAgain || sensorEntityId;

    const beforeAttrs = await getSensorAttributes(page, activeSensorEntityId);
    const beforeCount = (beforeAttrs.def_total_hours_array || []).length;
    expect(beforeCount).toBeGreaterThan(baselineCount);

    // Navigate to integration page
    await page.goto('/config/integrations/integration/ev_trip_planner');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('text=Integration entries', { timeout: 15000 });

    // Find and click Menu on the integration entry, then click Delete
    const allMenuButtons = page.getByRole('button', { name: 'Menu' });
    for (let i = 0; i < Math.min(await allMenuButtons.count(), 30); i++) {
      const menuBtn = allMenuButtons.nth(i);
      if (!await menuBtn.isVisible().catch(() => false)) continue;

      await menuBtn.click();
      await page.waitForTimeout(800);

      // Check if this is the integration entry menu (has Delete option)
      // Use getByText which penetrates shadow DOM reliably in Playwright
      const deleteOption = page.getByText('Delete', { exact: true });
      const deleteVisible = await deleteOption.isVisible().catch(() => false);

      // Also verify this is the integration menu (not device menu) by checking siblings
      const isIntegrationMenu = await deleteOption.evaluateAll((els) => {
        for (const el of els) {
          if (el.getBoundingClientRect().width === 0) continue;
          let parent: Element | null = el.parentElement;
          for (let j = 0; j < 5 && parent; j++) {
            const texts = Array.from(parent.children).map(c => c.textContent?.trim() || '');
            if (texts.includes('Reload') || texts.includes('Rename')) return true;
            parent = parent.parentElement;
          }
        }
        return false;
      });

      if (!deleteVisible || !isIntegrationMenu) {
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
        continue;
      }

      // Click Delete in the dropdown menu
      await deleteOption.click({ force: true });
      await page.waitForTimeout(1500);

      // Confirm the HA dialog. HA shows "Delete {name}?" with a Delete button.
      // Use Playwright to find and click the confirm button (it pierces shadow DOM).
      const confirmBtn = page.getByRole('button', { name: 'Delete' }).last();
      await expect(confirmBtn).toBeVisible({ timeout: 5000 });
      await confirmBtn.click({ force: true });
      break;
    }

    // Wait for deletion to propagate
    await page.waitForTimeout(5000);

    // Verify sensor no longer has trips from deleted integration
    let afterAttrs: Record<string, any> | null = null;
    try {
      afterAttrs = await getSensorAttributes(page, activeSensorEntityId);
    } catch (err: any) {
      if (err?.message?.includes('not found')) {
        // Sensor not found = integration properly deleted
        return;
      }
      throw err;
    }

    const afterCount = (afterAttrs.def_total_hours_array || []).length;
    expect(afterCount).toBe(baselineCount);
  });
});
