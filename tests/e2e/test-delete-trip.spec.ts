/**
 * E2E Test: Delete Trip
 *
 * Verifies that the EV Trip Planner panel correctly deletes a trip
 * through the UI form with confirmation dialog and calls the delete_trip service.
 * Usage:
 *   npx playwright test test-delete-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Delete Trip', () => {
  test('should show delete confirmation dialog', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler before clicking delete
    let dialogAccepted = false;

    page.on('dialog', async (dialog) => {
      dialogAccepted = true;
      console.log(`Dialog: ${dialog.message()}`);
      await dialog.accept();
    });

    // Click delete button on first trip
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const deleteButton = tripCards.first().locator('.delete-btn');

    if (await deleteButton.count() > 0) {
      await deleteButton.click();

      // Verify dialog appeared
      await page.waitForTimeout(500);
      expect(dialogAccepted).toBe(true);
    }
  });

  test('should delete trip when confirming', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Count trips before deletion
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripsBefore = await tripCards.count();

    if (tripsBefore > 0) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        console.log(`Dialog: ${dialog.message()}`);
        await dialog.accept();
      });

      // Click delete button on first trip
      const deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();

        // Wait for dialog
        await page.waitForTimeout(500);

        // Wait for trip to be removed
        await page.waitForTimeout(2000);

        // Verify trip count decreased
        const tripsAfter = await tripCards.count();
        expect(tripsAfter).toBeLessThan(tripsBefore);
      }
    }
  });

  test('should cancel deletion when declining', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Count trips before cancellation
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripsBefore = await tripCards.count();

    if (tripsBefore > 0) {
      // Set up dialog handler to cancel
      page.on('dialog', async (dialog) => {
        console.log(`Dialog: ${dialog.message()}`);
        await dialog.dismiss();
      });

      // Click delete button
      const deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();

        // Wait for dialog
        await page.waitForTimeout(500);

        // Verify trip count unchanged
        const tripsAfter = await tripCards.count();
        expect(tripsAfter).toBe(tripsBefore);
      }
    }
  });

  test('should show no trips after deleting last trip', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Count trips
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripsBefore = await tripCards.count();

    if (tripsBefore === 1) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Click delete button
      const deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();

        // Wait for trip to be removed
        await page.waitForTimeout(2000);

        // Verify "No hay viajes" appears
        const noTripsMessage = page.locator('ev-trip-planner-panel >> .no-trips');
        await expect(noTripsMessage).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should handle multiple deletions', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Count trips before
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripsBefore = await tripCards.count();

    if (tripsBefore >= 2) {
      // Set up dialog handler for multiple deletions
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Delete first trip
      let deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();
        await page.waitForTimeout(1000);

        // Delete second trip
        const tripCardsAfter = page.locator('ev-trip-planner-panel >> .trip-card');
        deleteButton = tripCardsAfter.first().locator('.delete-btn');

        if (await deleteButton.count() > 0) {
          await deleteButton.click();
          await page.waitForTimeout(1000);
        }
      }

      // Verify trip count decreased by 2
      const tripsAfter = await tripCards.count();
      expect(tripsAfter).toBeLessThanOrEqual(tripsBefore - 2);
    }
  });

  test('should update trips section after deletion', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trip count before
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripsBefore = await tripCards.count();

    if (tripsBefore > 0) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Delete a trip
      const deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();
        await page.waitForTimeout(1000);
      }

      // Verify trips section updated
      const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
      await expect(tripsSection).toBeVisible({ timeout: 10000 });
    }
  });

  test('should show add trip button after deletion', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Delete a trip if one exists
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripsBefore = await tripCards.count();

    if (tripsBefore > 0) {
      const deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();
        await page.waitForTimeout(1000);
      }
    }

    // Verify add trip button still visible
    const addTripButton = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripButton).toBeVisible({ timeout: 10000 });
  });
});
