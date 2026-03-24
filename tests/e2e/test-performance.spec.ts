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
test.describe('EV Trip Planner Performance Tests', () => {
  // Test configuration
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';
  const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
  const panelUrl = `${haUrl}/ev-trip-planner-${vehicleId}`;
  test('should measure panel load time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });
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
    const loadTime = Date.now() - startTime;
    console.log(`Panel load time: ${loadTime}ms`);
    // Panel should load in under 30 seconds
    expect(loadTime).toBeLessThan(30000);
  });
  test('should measure trip list load time', async ({ page }) => {
      () => (window as any)._tripPanel !== undefined,
    const listStartTime = Date.now();
    // Wait for trips section
    await page.waitForSelector('.trips-list', { timeout: 10000 });
    const listLoadTime = Date.now() - listStartTime;
    console.log(`Trip list load time: ${listLoadTime}ms`);
    // Trip list should load in under 10 seconds
    expect(listLoadTime).toBeLessThan(10000);
  test('should measure form open/close time', async ({ page }) => {
    // Measure form open time
    const formOpenStart = Date.now();
    await page.locator('.add-trip-btn').click();
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });
    const formOpenTime = Date.now() - formOpenStart;
    console.log(`Form open time: ${formOpenTime}ms`);
    // Measure form close time (after clicking cancel)
    const formCloseStart = Date.now();
    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.dismiss();
    // Find cancel button and click it
    const cancelButton = page.locator('.btn-cancel').first();
    if (await cancelButton.count() > 0) {
      await cancelButton.click();
    }
    // Wait for form to close
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });
    const formCloseTime = Date.now() - formCloseStart;
    console.log(`Form close time: ${formCloseTime}ms`);
    // Form operations should complete in under 5 seconds
    expect(formOpenTime + formCloseTime).toBeLessThan(5000);
  test('should measure complete CRUD operation time', async ({ page }) => {
      await dialog.accept();
    // Get initial trip count
    const initialCount = await page.locator('.trip-card').count();
    const crudStart = Date.now();
    // Create trip
    await page.selectOption('#trip-type', 'puntual');
    await page.fill('#trip-time', '10:00');
    await page.fill('#trip-km', '10.0');
    await page.click('.btn-primary');
    // Delete trip
    const trip = page.locator('.trip-card').last();
    await trip.locator('.delete-btn').click();
    const crudTime = Date.now() - crudStart;
    console.log(`Complete CRUD operation time: ${crudTime}ms`);
    // CRUD operation should complete in under 10 seconds
    expect(crudTime).toBeLessThan(10000);
  test('should measure total test suite time', async ({ page }) => {
    const suiteStartTime = Date.now();
    // Run a quick sequence of operations
    // Open and close form
    const suiteTime = Date.now() - suiteStartTime;
    console.log(`Test suite time: ${suiteTime}ms`);
    // This quick test should complete in under 60 seconds
    expect(suiteTime).toBeLessThan(60000);
  test('should measure memory usage', async ({ page }) => {
    // Get memory usage
    const memoryStats = await page.evaluate(() => {
      if (performance && performance.memory) {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize
        };
      }
      return null;
    if (memoryStats) {
      console.log(`Memory usage: ${Math.round(memoryStats.usedJSHeapSize / 1024 / 1024)}MB`);
      // Should not exceed 200MB for basic operations
      expect(memoryStats.usedJSHeapSize).toBeLessThan(200 * 1024 * 1024);
    } else {
      console.log('Memory stats not available (Chrome flags may be needed)');
});
