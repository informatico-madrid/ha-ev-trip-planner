/**
 * E2E Test: Panel Loading
 *
 * Verifies that the EV Trip Planner panel loads correctly and extracts
 * vehicle ID from the URL.
 *
 * Usage:
 *   npx playwright test test-panel-loading.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Panel Loading', () => {
  // Test configuration
  const vehicleId = 'chispitas';
  const panelUrl = `http://192.168.1.100:8123/ev-trip-planner-${vehicleId}`;

  // Setup before each test
  test.beforeEach(async ({ page }) => {
    // Clear console messages for cleaner test output
    page.off('console');
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.warn(`Console Error: ${msg.text()}`);
      }
    });
  });

  // Cleanup after each test
  test.afterEach(async ({ page }) => {
    // Cleanup can be extended if needed
  });

  test('should load panel at correct URL', async ({ page }) => {
    try {
      // Navigate to panel URL
      await page.goto(panelUrl, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      // Wait for panel to be ready
      // The panel sets window._tripPanel when it's ready
      await page.waitForFunction(
        (url) => {
          try {
            const panel = (window as any)._tripPanel;
            return panel !== undefined && panel._vehicleId !== undefined;
          } catch (e) {
            return false;
          }
        },
        panelUrl,
        { timeout: 30000 }
      );

      // Verify panel header contains vehicle name
      const header = page.locator('.panel-header');
      await expect(header).toBeVisible();

      // Verify vehicle ID is displayed
      const vehicleIdElement = page.locator('.vehicle-id');
      await expect(vehicleIdElement).toContainText(vehicleId);
    } catch (error) {
      // Take screenshot on failure for debugging
      await page.screenshot({ path: 'test-failure-panel-loading.png' });
      throw new Error(`Panel loading test failed: ${error.message}`);
    }
  });

  test('should extract vehicle ID from URL with /panel/ prefix', async ({ page }) => {
    try {
      // Test URL with /panel/ prefix (HA panel_custom format)
      const panelUrlWithPrefix = `http://192.168.1.100:8123/panel/ev-trip-planner-${vehicleId}`;

      await page.goto(panelUrlWithPrefix, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      // Wait for panel to be ready
      await page.waitForFunction(
        () => (window as any)._tripPanel !== undefined,
        { timeout: 30000 }
      );

      // Verify panel loaded successfully
      const header = page.locator('.panel-header');
      await expect(header).toBeVisible();
    } catch (error) {
      await page.screenshot({ path: 'test-failure-panel-prefix.png' });
      throw new Error(`Panel prefix test failed: ${error.message}`);
    }
  });

  test('should display vehicle name in panel header', async ({ page }) => {
    try {
      await page.goto(panelUrl, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      await page.waitForFunction(
        () => (window as any)._tripPanel !== undefined,
        { timeout: 30000 }
      );

      const vehicleName = 'Chispitas';
      await expect(page.locator('.panel-header')).toContainText(vehicleName);
    } catch (error) {
      await page.screenshot({ path: 'test-failure-vehicle-name.png' });
      throw new Error(`Vehicle name test failed: ${error.message}`);
    }
  });

  test('should show sensors section after panel loads', async ({ page }) => {
    try {
      await page.goto(panelUrl, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      await page.waitForFunction(
        () => (window as any)._tripPanel !== undefined,
        { timeout: 30000 }
      );

      const sensorsSection = page.locator('.sensors-section');
      await expect(sensorsSection).toBeVisible();
    } catch (error) {
      await page.screenshot({ path: 'test-failure-sensors.png' });
      throw new Error(`Sensors section test failed: ${error.message}`);
    }
  });

  test('should show trips section after panel loads', async ({ page }) => {
    try {
      await page.goto(panelUrl, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      await page.waitForFunction(
        () => (window as any)._tripPanel !== undefined,
        { timeout: 30000 }
      );

      const tripsSection = page.locator('.trips-section');
      await expect(tripsSection).toBeVisible();
    } catch (error) {
      await page.screenshot({ path: 'test-failure-trips.png' });
      throw new Error(`Trips section test failed: ${error.message}`);
    }
  });
});
