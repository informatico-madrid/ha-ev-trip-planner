/**
 * E2E Test: Panel Loading
 *
 * Usage:
 *   npx playwright test test-panel-loading.spec.ts
 */

import { test, expect } from '@playwright/test';

const HA_URL = process.env.HA_TEST_URL || 'http://192.168.1.201:18124';
const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner Panel Loading', () => {
  test('should load panel at correct URL', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify panel header
    const header = page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(header).toBeVisible({ timeout: 10000 });
  });

  test('should display vehicle name in panel header', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify panel header contains vehicle name
    const header = page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(header).toBeVisible({ timeout: 10000 });
    const headerText = await header.textContent();
    expect(headerText).toContain('Coche2');
  });

  test('should show sensors section after panel loads', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify sensors section is visible
    const sensorsSection = page.locator('ev-trip-planner-panel >> .sensors-section');
    await expect(sensorsSection).toBeVisible({ timeout: 10000 });
  });

  test('should show trips section after panel loads', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });
  });
});
