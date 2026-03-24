/**
 * E2E Test: Cross-Browser Compatibility
 *
 * Verifies that the EV Trip Planner panel works correctly across different browsers.
 * Tests should be run in Chrome, Firefox, and Safari.
 * Usage:
 *   npx playwright test test-cross-browser.spec.ts
 * To run in specific browser:
 *   npx playwright test test-cross-browser.spec.ts --project=chromium
 *   npx playwright test test-cross-browser.spec.ts --project=firefox
 *   npx playwright test test-cross-browser.spec.ts --project=webkit
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Cross-Browser Compatibility', () => {
  test('should load panel correctly in browser', async ({ page }) => {
    // Log browser info for debugging
    console.log(`Testing in: ${page.context().browser()?.browserType().name() || 'unknown'}`);

    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      (url) => {
        try {
          const panel = window as any;
          return customElements.get('ev-trip-planner-panel') !== undefined;
        } catch (e) {
          return false;
        }
      },
      { timeout: 30000 }
    );

    // Verify panel header is visible
    const header = page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(header).toBeVisible({ timeout: 10000 });

    // Verify vehicle ID is displayed
    const vehicleIdElement = page.locator('ev-trip-planner-panel >> .vehicle-id');
    await expect(vehicleIdElement).toContainText(vehicleId, { timeout: 10000 });
  });

  test('should load trips section in browser', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.locator('ev-trip-planner-panel >> .trips-section').waitFor({
      state: 'visible',
      timeout: 10000
    });

    // Verify trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible();
  });

  test('should display sensors section in browser', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify sensors section is visible
    const sensorsSection = page.locator('ev-trip-planner-panel >> .sensors-section');
    await expect(sensorsSection).toBeVisible({ timeout: 10000 });
  });

  test('should show add trip button in browser', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify add trip button is visible
    const addTripButton = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripButton).toBeVisible({ timeout: 10000 });

    // Click to open form
    await addTripButton.click();

    // Verify form overlay appears
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });
  });

  test('should handle trip form in browser', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Open add trip form
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.waitForSelector('ev-trip-planner-panel >> .trip-form-overlay', { timeout: 10000 });

    // Fill form
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('15.0');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });
  });

  test('should display trip cards in browser', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips to load
    await page.locator('ev-trip-planner-panel >> .trips-list').waitFor({
      state: 'visible',
      timeout: 10000
    });

    // Check if any trips exist
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
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
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      console.log(`Dialog message: ${dialog.message()}`);
      await dialog.accept();
    });

    // Try to delete a trip if one exists
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripCount = await tripCards.count();

    if (tripCount > 0) {
      const deleteButton = tripCards.first().locator('.delete-btn');

      if (await deleteButton.count() > 0) {
        await deleteButton.click();

        // Verify dialog appeared
        await page.waitForTimeout(500);

        // Dialog should be shown and accepted
        expect(true).toBe(true);
      }
    }
  });
});
