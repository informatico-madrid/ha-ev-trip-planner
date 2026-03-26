/**
 * E2E Test: Pause/Resume Trips
 *
 * Usage:
 *   npx playwright test test-pause-resume.spec.ts
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner - Pause/Resume', () => {
  /**
   * Setup: Navigate to panel URL
   */
  async function navigateToPanel(page: any): Promise<void> {
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  }

  test('should pause a recurring trip', async ({ page }) => {
    await navigateToPanel(page);

    // Find a recurring trip card
    const recurringTrip = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"]');
    await expect(recurringTrip).toBeVisible({ timeout: 10000 });

    // Click on the trip to open it
    await recurringTrip.first().click();

    // Click pause button
    const pauseButton = page.locator('ev-trip-planner-panel >> button[aria-label*="pause"]');
    await expect(pauseButton).toBeVisible({ timeout: 10000 });
    await pauseButton.click();

    // Wait for confirmation dialog
    const confirmButton = page.locator('ev-trip-planner-panel >> button:has-text("Confirm")');
    await expect(confirmButton).toBeVisible({ timeout: 10000 });
    await confirmButton.click();

    // Verify trip is now paused (check for pause indicator)
    const pausedTrip = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"][paused="true"]');
    await expect(pausedTrip.first()).toBeVisible({ timeout: 10000 });
  });

  test('should resume a paused trip', async ({ page }) => {
    await navigateToPanel(page);

    // Find a paused trip card
    const pausedTrip = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"][paused="true"]');

    if (await pausedTrip.count() > 0) {
      // Click on the paused trip to open it
      await pausedTrip.first().click();

      // Click resume button
      const resumeButton = page.locator('ev-trip-planner-panel >> button[aria-label*="resume"]');
      await expect(resumeButton).toBeVisible({ timeout: 10000 });
      await resumeButton.click();

      // Wait for confirmation dialog
      const confirmButton = page.locator('ev-trip-planner-panel >> button:has-text("Confirm")');
      await expect(confirmButton).toBeVisible({ timeout: 10000 });
      await confirmButton.click();

      // Verify trip is now active (no longer paused)
      const activeTrip = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"]:not([paused="true"])');
      await expect(activeTrip.first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('should toggle pause state with confirmation', async ({ page }) => {
    await navigateToPanel(page);

    // Get initial state - find a recurring trip
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"]');
    const initialCount = await tripCards.count();

    if (initialCount > 0) {
      // Click on the trip to open it
      await tripCards.first().click();

      // Click pause button
      const pauseButton = page.locator('ev-trip-planner-panel >> button[aria-label*="pause"]');
      await expect(pauseButton).toBeVisible({ timeout: 10000 });
      await pauseButton.click();

      // Confirm pause
      await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

      // Verify trip is now paused
      const pausedTrip = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"][paused="true"]');
      await expect(pausedTrip.first()).toBeVisible({ timeout: 10000 });

      // Click on the paused trip again
      await pausedTrip.first().click();

      // Click resume button
      const resumeButton = page.locator('ev-trip-planner-panel >> button[aria-label*="resume"]');
      await expect(resumeButton).toBeVisible({ timeout: 10000 });
      await resumeButton.click();

      // Confirm resume
      await page.locator('ev-trip-planner-panel >> button:has-text("Confirm")').click();

      // Verify trip is now active
      const activeTrip = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"]:not([paused="true"])');
      await expect(activeTrip.first()).toBeVisible({ timeout: 10000 });
    }
  });
});
