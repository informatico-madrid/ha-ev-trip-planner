/**
 * E2E Test: Delete Trip
 *
 * Usage:
 *   npx playwright test test-delete-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner - Delete Trip', () => {
  /**
   * Setup: Navigate to panel URL
   */
  async function navigateToPanel(page: any): Promise<void> {
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  }

  test('should show delete confirmation dialog', async ({ page }) => {
    await navigateToPanel(page);

    // Click on a trip card to open it
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await tripCard.click();

    // Find and click the delete button
    const deleteButton = page.locator('ev-trip-planner-panel >> button[aria-label*="delete"]');
    await expect(deleteButton).toBeVisible({ timeout: 10000 });
    await deleteButton.click();

    // Wait for confirmation dialog
    const dialog = page.locator('ev-trip-planner-panel >> .delete-dialog');
    await expect(dialog).toBeVisible({ timeout: 10000 });
  });

  test('should confirm deletion when confirmed', async ({ page }) => {
    await navigateToPanel(page);

    // Get initial trip count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialCount = await tripCards.count();

    if (initialCount > 0) {
      // Click on a trip card to open it
      await tripCards.first().click();

      // Click delete button
      const deleteButton = page.locator('ev-trip-planner-panel >> button[aria-label*="delete"]');
      await expect(deleteButton).toBeVisible({ timeout: 10000 });
      await deleteButton.click();

      // Wait for confirmation dialog and confirm
      const confirmButton = page.locator('ev-trip-planner-panel >> button:has-text("Confirm")');
      await expect(confirmButton).toBeVisible({ timeout: 10000 });
      await confirmButton.click();

      // Wait for trip to be deleted
      const finalCount = await tripCards.count();
      expect(finalCount).toBeLessThan(initialCount);
    }
  });

  test('should cancel deletion when cancelled', async ({ page }) => {
    await navigateToPanel(page);

    // Get initial trip count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialCount = await tripCards.count();

    if (initialCount > 0) {
      // Click on a trip card to open it
      await tripCards.first().click();

      // Click delete button
      const deleteButton = page.locator('ev-trip-planner-panel >> button[aria-label*="delete"]');
      await expect(deleteButton).toBeVisible({ timeout: 10000 });
      await deleteButton.click();

      // Wait for confirmation dialog and cancel
      const cancelButton = page.locator('ev-trip-planner-panel >> button:has-text("Cancel")');
      await expect(cancelButton).toBeVisible({ timeout: 10000 });
      await cancelButton.click();

      // Verify trip count didn't change
      const finalCount = await tripCards.count();
      expect(finalCount).toBe(initialCount);
    }
  });

  test('should handle deletion of multiple trips', async ({ page }) => {
    await navigateToPanel(page);

    // Get initial trip count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialCount = await tripCards.count();

    if (initialCount >= 2) {
      // Delete multiple trips
      for (let i = 0; i < 2 && i < initialCount; i++) {
        await tripCards.nth(i).click();

        // Click delete and confirm
        await page.locator('ev-trip-planner-panel >> button[aria-label*="delete"]').click();
        await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

        await page.waitForTimeout(1000);
      }

      // Verify trip count decreased
      const finalCount = await tripCards.count();
      expect(finalCount).toBeLessThan(initialCount);
    }
  });
});
