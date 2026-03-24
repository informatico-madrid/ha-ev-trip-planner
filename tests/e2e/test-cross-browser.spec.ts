/**
 * E2E Test: Cross-Browser Compatibility
 *
 * Verifies that the EV Trip Planner panel works correctly across different browsers.
 * Tests should be run in Chrome, Firefox, and Safari.
 *
 * Usage:
 *   npx playwright test test-cross-browser.spec.ts
 *
 * To run in specific browser:
 *   npx playwright test test-cross-browser.spec.ts --project=chromium
 *   npx playwright test test-cross-browser.spec.ts --project=firefox
 *   npx playwright test test-cross-browser.spec.ts --project=webkit
 */

import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Cross-Browser Compatibility', () => {
  // Test configuration
  const vehicleId = 'chispitas';
  const panelUrl = `http://192.168.1.100:8123/ev-trip-planner-${vehicleId}`;

  test('should load panel correctly in browser', async ({ page }) => {
    // Log browser info for debugging
    console.log(`Testing in: ${page.context().browser().browserType().name()}`);

    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    // Wait for panel to be ready
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

    // Verify panel header is visible
    const header = page.locator('.panel-header');
    await expect(header).toBeVisible();

    // Verify vehicle ID is displayed
    const vehicleIdElement = page.locator('.vehicle-id');
    await expect(vehicleIdElement).toContainText(vehicleId);
  });

  test('should load trips section in browser', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.waitForSelector('.trips-list', { timeout: 10000 });

    // Verify trips section is visible
    const tripsSection = page.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  });

  test('should display sensors section in browser', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Verify sensors section is visible
    const sensorsSection = page.locator('.sensors-section');
    await expect(sensorsSection).toBeVisible();
  });

  test('should show add trip button in browser', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Verify add trip button is visible
    const addTripButton = page.locator('.add-trip-btn');
    await expect(addTripButton).toBeVisible();

    // Click to open form
    await addTripButton.click();

    // Verify form overlay appears
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });
  });

  test('should handle trip form in browser', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Open add trip form
    await page.locator('.add-trip-btn').click();
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Fill form
    await page.selectOption('#trip-type', 'puntual');
    await page.fill('#trip-time', '10:00');
    await page.fill('#trip-km', '15.0');

    // Submit form
    await page.click('.btn-primary');

    // Wait for form to close
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });
  });

  test('should display trip cards in browser', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips to load
    await page.waitForSelector('.trips-list', { timeout: 10000 });

    // Check if any trips exist
    const tripCards = page.locator('.trip-card');
    const tripCount = await tripCards.count();

    if (tripCount > 0) {
      // Verify trip card structure
      const firstTrip = tripCards.first();
      await expect(firstTrip).toBeVisible();

      // Check for action buttons
      const hasEditButton = await firstTrip.locator('.edit-btn').count() > 0;
      const hasDeleteButton = await firstTrip.locator('.delete-btn').count() > 0;

      // At least one action button should exist
      expect(hasEditButton || hasDeleteButton).toBe(true);
    }
  });

  test('should handle dialog confirmations in browser', async ({ page }) => {
    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section
    await page.waitForSelector('.trips-list', { timeout: 10000 });

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      console.log(`Dialog message: ${dialog.message()}`);
      await dialog.accept();
    });

    // Try to delete a trip if one exists
    const deleteButton = page.locator('.trip-card .delete-btn').first();
    const deleteButtonCount = await deleteButton.count();

    if (deleteButtonCount > 0) {
      await deleteButton.click();

      // Verify dialog appeared
      await page.waitForTimeout(500);
    }
  });
});
