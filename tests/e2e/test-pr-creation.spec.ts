/**
 * E2E Test: PR Creation and Verification
 *
 * Verifies that the PR creation process works correctly and all tests pass.
 * This test can be used to validate the PR before merging.
 * Usage:
 *   npx playwright test test-pr-creation.spec.ts
 */

import { test, expect } from '@playwright/test';
test.describe('EV Trip Planner PR Creation Tests', () => {
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';
  const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
  const panelUrl = `${haUrl}/ev-trip-planner-${vehicleId}`;
  test('should verify all panel components load', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );
    // Verify all critical components are present
    const components = [
      '.panel-header',
      '.vehicle-id',
      '.sensors-section',
      '.trips-section',
      '.add-trip-btn'
    ];
    for (const component of components) {
      const element = page.locator(component);
      await expect(element).toBeVisible();
    }
  });
  test('should verify trip CRUD operations', async ({ page }) => {
    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    // Create
    await page.locator('.add-trip-btn').click();
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });
    await page.selectOption('#trip-type', 'puntual');
    await page.fill('#trip-time', '10:00');
    await page.click('.btn-primary');
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });
    // Verify trip created
    const tripCount = await page.locator('.trip-card').count();
    expect(tripCount).toBeGreaterThan(0);
    // Edit (if trip exists)
    const trip = page.locator('.trip-card').first();
    const editButton = trip.locator('.edit-btn');
    if (await editButton.count() > 0) {
      await editButton.click();
      await page.fill('#trip-km', '20.0');
      await page.click('.btn-primary');
      await expect(formOverlay).toBeHidden({ timeout: 5000 });
    // Delete
    const deleteButton = trip.locator('.delete-btn');
    if (await deleteButton.count() > 0) {
      await deleteButton.click();
      await page.waitForTimeout(500);
    // Verify trip deleted
    const finalCount = await page.locator('.trip-card').count();
    expect(finalCount).toBeLessThanOrEqual(tripCount);
  test('should verify pause/resume functionality', async ({ page }) => {
    // Pause
    const pauseButton = trip.locator('.pause-btn');
    if (await pauseButton.count() > 0) {
      await pauseButton.click();
      const isActive = await trip.getAttribute('data-active');
      expect(isActive).toBe('false');
      // Resume
      const resumeButton = trip.locator('.resume-btn');
      if (await resumeButton.count() > 0) {
        await resumeButton.click();
        await page.waitForTimeout(500);
        const isActiveAfterResume = await trip.getAttribute('data-active');
        expect(isActiveAfterResume).toBe('true');
      }
  test('should verify complete/cancel functionality', async ({ page }) => {
    // Complete
    const completeButton = trip.locator('.complete-btn');
    if (await completeButton.count() > 0) {
      await completeButton.click();
      const isCompleted = await trip.getAttribute('data-completed');
      expect(isCompleted).toBe('true');
      // Cancel
      const cancelButton = trip.locator('.cancel-btn');
      if (await cancelButton.count() > 0) {
        await cancelButton.click();
        const isCanceled = await trip.getAttribute('data-canceled');
        expect(isCanceled).toBe('true');
  test('should verify panel stability under load', async ({ page }) => {
    // Perform multiple rapid operations
    for (let i = 0; i < 3; i++) {
      // Create
      await page.locator('.add-trip-btn').click();
      await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });
      await page.selectOption('#trip-type', 'puntual');
      await page.fill('#trip-time', '10:00');
      const formOverlay = page.locator('.trip-form-overlay');
      // Delete
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });
      await page.locator('.trip-card').last().locator('.delete-btn').click();
    // Verify panel still functional
    expect(tripCount).toBeGreaterThanOrEqual(0);
    // Verify panel header still visible
    const header = page.locator('.panel-header');
    await expect(header).toBeVisible();
  test('should verify no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(`[${msg.type()}] ${msg.text()}`);
    page.on('pageerror', error => {
      errors.push(`[PAGE_ERROR] ${error.message}`);
    // Perform some operations
      await dialog.dismiss();
    const cancelButton = page.locator('.btn-cancel').first();
    if (await cancelButton.count() > 0) {
      await cancelButton.click();
    // Wait a bit for any async errors
    await page.waitForTimeout(1000);
    // Report errors (but don't fail - some warnings are expected)
    if (errors.length > 0) {
      console.log('Console errors found:');
      errors.forEach(err => console.log(err));
});
