import { test, expect } from '@playwright/test';
import { HA_URL, VEHICLE_ID } from './env';

test.describe('Trip States Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, { waitUntil: 'domcontentloaded' });
  });

  test('should pause a recurring trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    await page.on('dialog', async dialog => {
      await dialog.accept();
    });

    const pauseButtons = page.locator('ev-trip-planner-panel >> .pause-btn');

    if (await pauseButtons.count() > 0) {
      await pauseButtons.first().click();

      await expect(pauseButtons.first()).toBeHidden();

      const firstCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
      await expect(firstCard).toHaveAttribute('data-active', 'false');

      const badge = firstCard.locator('.status-badge');
      await expect(badge).toContainText('Inactivo');
    }
  });

  test('should resume a paused trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    await page.on('dialog', async dialog => {
      await dialog.accept();
    });

    const resumeButtons = page.locator('ev-trip-planner-panel >> .resume-btn');

    if (await resumeButtons.count() > 0) {
      await resumeButtons.first().click();

      await expect(resumeButtons.first()).toBeHidden();

      const firstCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
      await expect(firstCard).toHaveAttribute('data-active', 'true');

      const badge = firstCard.locator('.status-badge');
      await expect(badge).toContainText('Activo');
    }
  });

  test('should complete a punctual trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    const completeButtons = page.locator('ev-trip-planner-panel >> .complete-btn');

    if (await completeButtons.count() > 0) {
      await completeButtons.first().click();

      await expect(completeButtons.first()).toBeHidden();

      const firstCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
      const badge = firstCard.locator('.status-badge');

      await expect(badge).toContainText('Completado');

      const actionButtons = firstCard.locator('.trip-action-btn');
      await expect(actionButtons).toHaveCount(0);
    }
  });

  test('should cancel a punctual trip', async ({ page }) => {
    await page.locator('ev-trip-planner-panel').first().waitFor({ state: 'attached' });

    await page.on('dialog', async dialog => {
      await dialog.accept();
    });

    const cancelButtons = page.locator('ev-trip-planner-panel >> .cancel-btn');

    if (await cancelButtons.count() > 0) {
      await cancelButtons.first().click();

      await expect(cancelButtons.first()).toBeHidden();

      const firstCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
      const badge = firstCard.locator('.status-badge');

      await expect(badge).toContainText('Cancelado');

      const actionButtons = firstCard.locator('.trip-action-btn');
      await expect(actionButtons).toHaveCount(0);
    }
  });
});
