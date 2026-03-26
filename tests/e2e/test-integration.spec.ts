/**
 * E2E Test: Integration - Full CRUD Workflow
 *
 * Usage:
 *   npx playwright test test-integration.spec.ts
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner - Full CRUD Integration', () => {
  /**
   * Setup: Navigate to panel URL
   */
  async function navigateToPanel(page: any): Promise<void> {
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  }

  test('should execute complete CRUD workflow', async ({ page }) => {
    await navigateToPanel(page);

    // CREATE: Add a new recurring trip
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('4.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test recurring trip');

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // READ: Verify trip was created
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripCount = await tripCards.count();
    expect(tripCount).toBeGreaterThanOrEqual(1);

    // UPDATE: Edit the trip
    await tripCards.first().click();

    // Modify time
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('12:00');

    // Submit update
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // READ: Verify update persisted
    const updatedTrip = tripCards.first();
    await expect(updatedTrip).toContainText('12:00');

    // DELETE: Delete the trip
    await updatedTrip.click();

    // Click delete button
    await page.locator('ev-trip-planner-panel >> button[aria-label*="delete"]').click();

    // Confirm deletion
    await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

    // Wait for deletion
    await page.waitForTimeout(1000);

    // READ: Verify trip was deleted
    const finalTripCount = await tripCards.count();
    expect(finalTripCount).toBeLessThan(tripCount);
  });

  test('should handle multiple CRUD operations in sequence', async ({ page }) => {
    await navigateToPanel(page);

    const initialCount = await page.locator('ev-trip-planner-panel >> .trip-card').count();

    // CREATE: Add multiple trips
    for (let i = 0; i < 3; i++) {
      await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

      await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
      await page.locator('ev-trip-planner-panel >> #trip-day').selectOption(i + 1);
      await page.locator('ev-trip-planner-panel >> #trip-time').fill('09:00');
      await page.locator('ev-trip-planner-panel >> #trip-km').fill('20.0');
      await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('3.0');
      await page.locator('ev-trip-planner-panel >> #trip-description').fill(`Test trip ${i + 1}`);

      await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

      const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
      await expect(formOverlay).toBeHidden({ timeout: 10000 });
    }

    // READ: Verify all trips were created
    const createdCount = await page.locator('ev-trip-planner-panel >> .trip-card').count();
    expect(createdCount).toBeGreaterThanOrEqual(initialCount + 3);

    // UPDATE: Update first trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().click();
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('14:00');
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // DELETE: Delete one trip
    await page.locator('ev-trip-planner-panel >> .trip-card').nth(1).click();
    await page.locator('ev-trip-planner-panel >> button[aria-label*="delete"]').click();
    await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();
    await page.waitForTimeout(1000);

    // READ: Verify final count
    const finalCount = await page.locator('ev-trip-planner-panel >> .trip-card').count();
    expect(finalCount).toBeLessThan(createdCount);
  });
});
