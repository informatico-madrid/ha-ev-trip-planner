import { test, expect } from '@playwright/test';

test.describe('Trip CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    await page.waitForFunction(() => customElements.get('ev-trip-planner-panel'), {
      timeout: 10000
    });
  });

  test('should create a recurring trip', async ({ page }) => {
    await page.waitForSelector('ev-trip-planner-panel', { timeout: 10000 });

    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await addTripBtn.click();

    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeVisible();

    await page.selectOption('#trip-type', 'recurrente');
    await page.selectOption('#trip-day', '1');
    await page.fill('#trip-time', '08:00');
    await page.fill('#trip-km', '25.5');
    await page.fill('#trip-kwh', '5.2');
    await page.fill('#trip-description', 'Test trip');

    await page.locator('button[type="submit"]').click();

    await expect(formOverlay).toBeHidden();

    const tripCards = page.locator('.trip-card');
    await expect(tripCards).toHaveCount(1);
  });

  test('should edit an existing trip', async ({ page }) => {
    await page.waitForSelector('ev-trip-planner-panel', { timeout: 10000 });

    const tripCards = page.locator('.trip-card');
    if (await tripCards.count() > 0) {
      await page.locator('.trip-action-btn.edit-btn').first().click();

      const formOverlay = page.locator('.trip-form-overlay');
      await expect(formOverlay).toBeVisible();

      await page.fill('#edit-trip-time', '14:30');
      await page.fill('#edit-trip-km', '40.0');

      await page.locator('button[type="submit"]').click();

      await expect(formOverlay).toBeHidden();

      await expect(page.locator('.trip-card')).toContainText('40.0 km');
      await expect(page.locator('.trip-card')).toContainText('14:30');
    }
  });

  test('should delete an existing trip', async ({ page }) => {
    await page.waitForSelector('ev-trip-planner-panel', { timeout: 10000 });

    const tripCards = page.locator('.trip-card');
    if (await tripCards.count() > 0) {
      await page.on('dialog', async dialog => {
        await dialog.accept();
      });

      await page.locator('.trip-action-btn.delete-btn').first().click();

      await page.waitForSelector('.no-trips');

      const noTrips = page.locator('.no-trips');
      const remainingTrips = page.locator('.trip-card');

      if (await noTrips.count() > 0) {
        await expect(noTrips).toBeVisible();
      } else {
        await expect(remainingTrips).not.toHaveCount(1);
      }
    }
  });
});
