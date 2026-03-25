import { test, expect } from '@playwright/test';

import { HA_URL, VEHICLE_ID } from './env';

test.describe('Trip CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, { waitUntil: 'domcontentloaded' });
  });

  test('should create a recurring trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await addTripBtn.click();

    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible();

    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('08:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.2');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test trip');

    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    await expect(formOverlay).toBeHidden();

    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards.count()).resolves.toBeGreaterThan(0);
  });

  test('should edit an existing trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    if (await tripCards.count() > 0) {
      await page.locator('ev-trip-planner-panel >> .trip-action-btn.edit-btn').first().click();

      const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
      await expect(formOverlay).toBeVisible();

      await page.locator('ev-trip-planner-panel >> #edit-trip-time').fill('14:30');
      await page.locator('ev-trip-planner-panel >> #edit-trip-km').fill('40.0');

      await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

      await expect(formOverlay).toBeHidden();

      await expect(tripCards).toContainText('40.0 km');
      await expect(tripCards).toContainText('14:30');
    }
  });

  test('should delete an existing trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialCount = await tripCards.count();

    if (initialCount > 0) {
      // Set up dialog handler before click
      page.on('dialog', async dialog => {
        await dialog.accept();
      });

      await page.locator('ev-trip-planner-panel >> .trip-action-btn.delete-btn').first().click();

      // Wait for deletion to complete
      const currentCount = await tripCards.count();
      await expect(currentCount).toBeLessThanOrEqual(initialCount);

      // Check for empty state if last trip was deleted
      const noTrips = page.locator('ev-trip-planner-panel >> .no-trips');
      if (currentCount === 0) {
        await expect(noTrips).toBeVisible();
      }
    }
  });
});
