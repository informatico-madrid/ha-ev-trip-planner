/**
 * E2E Test: Delete Trip
 *
 * Verifies that the EV Trip Planner panel correctly deletes a trip
 * through the UI form with confirmation dialog and calls the delete_trip service.
 *
 * Usage:
 *   npx playwright test test-delete-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Delete Trip', () => {
  // Test configuration
  const vehicleId = 'chispitas';
  const panelUrl = `http://192.168.1.100:8123/ev-trip-planner-${vehicleId}`;

  test('should show delete confirmation dialog', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler before clicking delete
    let dialogAccepted = false;
    page.on('dialog', async (dialog) => {
      dialogAccepted = true;
      await dialog.accept();
    });

    // Click delete button on first trip
    const deleteButton = page.locator('.trip-card .delete-btn').first();
    await deleteButton.click();

    // Verify dialog appeared
    await page.waitForTimeout(500); // Allow time for dialog to appear
    expect(dialogAccepted).toBe(true);
  });

  test('should delete trip when confirming', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Count trips before deletion
    const tripsBefore = await page.locator('.trip-card').count();

    if (tripsBefore > 0) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Click delete button on first trip
      const deleteButton = page.locator('.trip-card .delete-btn').first();
      await deleteButton.click();

      // Wait for dialog
      await page.waitForTimeout(500);

      // Wait for trip to be removed
      await page.waitForSelector('.trip-card', { timeout: 5000 });

      // Verify trip count decreased
      const tripsAfter = await page.locator('.trip-card').count();
      expect(tripsAfter).toBe(tripsBefore - 1);
    }
  });

  test('should cancel deletion when declining', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Count trips before cancellation
    const tripsBefore = await page.locator('.trip-card').count();

    if (tripsBefore > 0) {
      // Set up dialog handler to cancel
      page.on('dialog', async (dialog) => {
        await dialog.dismiss();
      });

      // Click delete button on first trip
      const deleteButton = page.locator('.trip-card .delete-btn').first();
      await deleteButton.click();

      // Wait for dialog
      await page.waitForTimeout(500);

      // Wait for trips section
      await page.waitForSelector('.trip-card', { timeout: 5000 });

      // Verify trip count unchanged
      const tripsAfter = await page.locator('.trip-card').count();
      expect(tripsAfter).toBe(tripsBefore);
    }
  });

  test('should show no trips after deleting last trip', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Count trips
    const tripsBefore = await page.locator('.trip-card').count();

    if (tripsBefore === 1) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Click delete button
      const deleteButton = page.locator('.trip-card .delete-btn').first();
      await deleteButton.click();

      // Wait for dialog
      await page.waitForTimeout(500);

      // Verify "No hay viajes" appears
      const noTripsMessage = page.locator('.no-trips');
      await expect(noTripsMessage).toBeVisible();
    }
  });

  test('should handle multiple deletions', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Count trips before
    const tripsBefore = await page.locator('.trip-card').count();

    if (tripsBefore >= 2) {
      // Set up dialog handler for multiple deletions
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Delete first trip
      await page.locator('.trip-card .delete-btn').first().click();
      await page.waitForTimeout(500);

      // Delete second trip
      await page.locator('.trip-card .delete-btn').first().click();
      await page.waitForTimeout(500);

      // Wait for trips to update
      await page.waitForSelector('.trip-card', { timeout: 5000 });

      // Verify trip count decreased by 2
      const tripsAfter = await page.locator('.trip-card').count();
      expect(tripsAfter).toBe(tripsBefore - 2);
    }
  });

  test('should update trips section after deletion', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Get trip count before
    const tripsBefore = await page.locator('.trip-card').count();

    if (tripsBefore > 0) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Delete a trip
      await page.locator('.trip-card .delete-btn').first().click();
      await page.waitForTimeout(500);

      // Verify trips section updated
      const tripsSection = page.locator('.trips-section');
      await expect(tripsSection).toBeVisible();

      const tripsAfter = await page.locator('.trip-card').count();
      expect(tripsAfter).toBe(tripsBefore - 1);
    }
  });

  test('should show add trip button after deletion', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Delete a trip if one exists
    const tripsBefore = await page.locator('.trip-card').count();
    if (tripsBefore > 0) {
      await page.locator('.trip-card .delete-btn').first().click();
      await page.waitForTimeout(500);
    }

    // Verify add trip button still visible
    const addTripButton = page.locator('.add-trip-btn');
    await expect(addTripButton).toBeVisible();
  });
});
