/**
 * E2E Test: Complete/Cancel Punctual Trips
 *
 * Usage:
 *   npx playwright test test-complete-cancel.spec.ts
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner - Complete/Cancel', () => {
  /**
   * Setup: Navigate to panel URL
   */
  async function navigateToPanel(page: any): Promise<void> {
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  }

  test('should complete a punctual trip', async ({ page }) => {
    await navigateToPanel(page);

    // Find a punctual trip card
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"]');
    await expect(punctualTrip).toBeVisible({ timeout: 10000 });

    // Click on the trip to open it
    await punctualTrip.first().click();

    // Click complete button
    const completeButton = page.locator('ev-trip-planner-panel >> button[aria-label*="complete"]');
    await expect(completeButton).toBeVisible({ timeout: 10000 });
    await completeButton.click();

    // Wait for confirmation dialog
    const confirmButton = page.locator('ev-trip-planner-panel >> button:has-text("Confirm")');
    await expect(confirmButton).toBeVisible({ timeout: 10000 });
    await confirmButton.click();

    // Verify trip is now completed (check for complete indicator)
    const completedTrip = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="completed"]');
    await expect(completedTrip.first()).toBeVisible({ timeout: 10000 });
  });

  test('should cancel a pending punctual trip', async ({ page }) => {
    await navigateToPanel(page);

    // Find a pending punctual trip card
    const pendingTrip = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="pending"]');
    await expect(pendingTrip).toBeVisible({ timeout: 10000 });

    // Click on the trip to open it
    await pendingTrip.first().click();

    // Click cancel button
    const cancelButton = page.locator('ev-trip-planner-panel >> button[aria-label*="cancel"]');
    await expect(cancelButton).toBeVisible({ timeout: 10000 });
    await cancelButton.click();

    // Wait for confirmation dialog
    const confirmButton = page.locator('ev-trip-planner-panel >> button:has-text("Confirm")');
    await expect(confirmButton).toBeVisible({ timeout: 10000 });
    await confirmButton.click();

    // Verify trip is cancelled
    const cancelledTrip = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="cancelled"]');
    await expect(cancelledTrip.first()).toBeVisible({ timeout: 10000 });
  });

  test('should toggle status with confirmation', async ({ page }) => {
    await navigateToPanel(page);

    // Get initial state - find a punctual trip
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"]');
    const initialCount = await tripCards.count();

    if (initialCount > 0) {
      // Click on the trip to open it
      await tripCards.first().click();

      // Click complete button
      const completeButton = page.locator('ev-trip-planner-panel >> button[aria-label*="complete"]');
      await expect(completeButton).toBeVisible({ timeout: 10000 });
      await completeButton.click();

      // Confirm complete
      await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

      // Verify trip is now completed
      const completedTrip = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="completed"]');
      await expect(completedTrip.first()).toBeVisible({ timeout: 10000 });

      // Click on the completed trip again
      await completedTrip.first().click();

      // Click cancel button
      const cancelButton = page.locator('ev-trip-planner-panel >> button[aria-label*="cancel"]');
      await expect(cancelButton).toBeVisible({ timeout: 10000 });
      await cancelButton.click();

      // Confirm cancel
      await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

      // Verify trip is now cancelled
      const cancelledTrip = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="cancelled"]');
      await expect(cancelledTrip.first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('should handle multiple trip status changes', async ({ page }) => {
    await navigateToPanel(page);

    // Get initial count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"]');
    const initialCount = await tripCards.count();

    if (initialCount >= 2) {
      // Complete one trip
      await tripCards.first().click();
      await page.locator('ev-trip-planner-panel >> button[aria-label*="complete"]').click();
      await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

      // Wait a bit
      await page.waitForTimeout(1000);

      // Cancel another trip
      const remainingTrips = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"]');
      await remainingTrips.first().click();
      await page.locator('ev-trip-planner-panel >> button[aria-label*="cancel"]').click();
      await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

      // Verify both changes
      const completedCount = await page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="completed"]').count();
      const cancelledCount = await page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"][status="cancelled"]').count();

      expect(completedCount).toBeGreaterThanOrEqual(1);
      expect(cancelledCount).toBeGreaterThanOrEqual(1);
    }
  });
});
