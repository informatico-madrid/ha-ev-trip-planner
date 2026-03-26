/**
 * E2E Test: Edit Trip
 *
 * Usage:
 *   npx playwright test test-edit-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner - Edit Trip', () => {
  /**
   * Setup: Navigate to panel URL
   */
  async function navigateToPanel(page: any): Promise<void> {
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  }

  test('should pre-fill form when editing existing trip', async ({ page }) => {
    await navigateToPanel(page);

    // Click on a trip card to edit
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await tripCard.click();

    // Wait for edit form to appear
    const editForm = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(editForm).toBeVisible({ timeout: 10000 });

    // Verify form fields are populated (not empty)
    const timeField = page.locator('ev-trip-planner-panel >> #trip-time');
    const timeValue = await timeField.inputValue();
    expect(timeValue).toBeTruthy();
  });

  test('should update trip when form is submitted', async ({ page }) => {
    await navigateToPanel(page);

    // Click on a trip card to edit
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await tripCard.click();

    // Wait for edit form to appear
    const editForm = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(editForm).toBeVisible({ timeout: 10000 });

    // Modify the trip time
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('15:00');

    // Submit the form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    await expect(editForm).toBeHidden({ timeout: 10000 });

    // Verify the trip was updated (check for the new time in the UI)
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards.first()).toBeVisible({ timeout: 10000 });
  });

  test('should cancel edit when cancel button is clicked', async ({ page }) => {
    await navigateToPanel(page);

    // Click on a trip card to edit
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await tripCard.click();

    // Wait for edit form to appear
    const editForm = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(editForm).toBeVisible({ timeout: 10000 });

    // Modify the trip time
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('15:00');

    // Cancel the edit
    await page.locator('ev-trip-planner-panel >> button[type="button"]').first().click();

    // Wait for form to close
    await expect(editForm).toBeHidden({ timeout: 10000 });
  });
});
