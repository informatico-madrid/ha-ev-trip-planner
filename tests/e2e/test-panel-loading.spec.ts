/**
 * E2E Test: Panel Loading
 *
 * Usage:
 *   npx playwright test test-panel-loading.spec.ts
 *
 * Requires HA_URL environment variable:
 *   export HA_URL=http://192.168.1.201:18124
 */

import { test, expect } from '@playwright/test';
import { TripPanel } from './test-base.spec';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner Panel Loading', () => {
  /**
   * Navigate to panel - uses hass-taste-test authenticated URL
   * NO MANUAL LOGIN required - dashboard.link() provides auth automatically
   */
  async function navigateToPanel(page: any): Promise<void> {
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  }

  test('should load panel at correct URL', async ({ page }) => {
    await navigateToPanel(page);

    // Verify panel header is visible by penetrating Shadow DOM
    const header = page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(header).toBeVisible({ timeout: 10000 });
  });

  test('should display vehicle name in panel header', async ({ page }) => {
    await navigateToPanel(page);

    // Verify panel header contains vehicle name
    const header = page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(header).toBeVisible({ timeout: 10000 });
    const headerText = await header.textContent();
    expect(headerText).toContain(VEHICLE_ID);
  });

  test('should show sensors section after panel loads', async ({ page }) => {
    await navigateToPanel(page);

    // Verify sensors section is visible
    const sensorsSection = page.locator('ev-trip-planner-panel >> .sensors-section');
    await expect(sensorsSection).toBeVisible({ timeout: 15000 });
  });

  test('should show trips section after panel loads', async ({ page }) => {
    await navigateToPanel(page);

    // Verify trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 15000 });
  });
});
