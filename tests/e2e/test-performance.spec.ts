/**
 * E2E Test: Performance Testing
 *
 * Verifies that the EV Trip Planner panel performs within acceptable limits.
 * Total test time should be < 5 minutes for the full test suite.
 * Usage:
 *   npx playwright test test-performance.spec.ts
 * Performance targets:
 * - Panel load time: < 30 seconds
 * - Trip list load time: < 10 seconds
 * - Form open/close: < 5 seconds
 * - Total test suite: < 5 minutes
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Performance Tests', () => {
  test('should measure panel load time', async ({ page }) => {
    const startTime = Date.now();

    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    const loadTime = Date.now() - startTime;
    console.log(`Panel load time: ${loadTime}ms`);

    // Panel should load in under 30 seconds
    expect(loadTime).toBeLessThan(30000);
  });

  test('should measure trip list load time', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    const listStartTime = Date.now();

    // Wait for trips section
    await page.locator('ev-trip-planner-panel >> .trips-section').waitFor({
      state: 'visible',
      timeout: 10000
    });

    const listLoadTime = Date.now() - listStartTime;
    console.log(`Trip list load time: ${listLoadTime}ms`);

    // Trip list should load in under 10 seconds
    expect(listLoadTime).toBeLessThan(10000);
  });

  test('should measure form open/close time', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Measure form open time
    const formOpenStart = Date.now();

    // Open form
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.waitForSelector('ev-trip-planner-panel >> .trip-form-overlay', { timeout: 10000 });

    const formOpenTime = Date.now() - formOpenStart;
    console.log(`Form open time: ${formOpenTime}ms`);

    // Measure form close time (after clicking cancel)
    const formCloseStart = Date.now();

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.dismiss();
    });

    // Click submit to close form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });

    const formCloseTime = Date.now() - formCloseStart;
    console.log(`Form close time: ${formCloseTime}ms`);

    // Form operations should complete in under 5 seconds
    expect(formOpenTime + formCloseTime).toBeLessThan(5000);
  });

  test('should measure complete CRUD operation time', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Get initial trip count
    const initialCount = await page.locator('ev-trip-planner-panel >> .trip-card').count();

    const crudStart = Date.now();

    // Create trip
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
    await page.locator('ev-trip-planner-panel >> #trip-datetime').fill('2026-03-25T10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await page.waitForTimeout(500);

    // Delete trip
    const trip = page.locator('ev-trip-planner-panel >> .trip-card').last();
    await trip.locator('.delete-btn').click();
    await page.waitForTimeout(500);

    const crudTime = Date.now() - crudStart;
    console.log(`Complete CRUD operation time: ${crudTime}ms`);

    // CRUD operation should complete in under 10 seconds
    expect(crudTime).toBeLessThan(10000);
  });

  test('should measure total test suite time', async ({ page }) => {
    const suiteStartTime = Date.now();

    // Run a quick sequence of operations
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Open and close form
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    const suiteTime = Date.now() - suiteStartTime;
    console.log(`Test suite time: ${suiteTime}ms`);

    // This quick test should complete in under 60 seconds
    expect(suiteTime).toBeLessThan(60000);
  });

  test('should measure memory usage', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get memory usage
    const memoryStats = await page.evaluate(() => {
      if (performance && (performance as any).memory) {
        return {
          usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
          totalJSHeapSize: (performance as any).memory.totalJSHeapSize
        };
      }
      return null;
    });

    if (memoryStats) {
      console.log(`Memory usage: ${Math.round(memoryStats.usedJSHeapSize / 1024 / 1024)}MB`);

      // Should not exceed 200MB for basic operations
      expect(memoryStats.usedJSHeapSize).toBeLessThan(200 * 1024 * 1024);
    } else {
      console.log('Memory stats not available (Chrome flags may be needed)');
    }
  });
});
