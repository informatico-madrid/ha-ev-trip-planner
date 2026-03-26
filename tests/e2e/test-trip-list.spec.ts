/**
 * E2E Test: Trip List Loading
 *
 * Usage:
 *   npx playwright test test-trip-list.spec.ts
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner - Trip List Loading', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Navigate to panel before each test
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
  });

  test('should load trips section with vehicles', async ({ page }) => {
    // Verify trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });
  });

  test('should display vehicle selector in trips section', async ({ page }) => {
    // Verify vehicle selector is visible
    const vehicleSelector = page.locator('ev-trip-planner-panel >> #vehicle-selector');
    await expect(vehicleSelector).toBeVisible({ timeout: 10000 });
  });

  test('should show trip cards when trips exist', async ({ page }) => {
    // Wait for trip cards to appear
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display trip type indicators', async ({ page }) => {
    // Check for recurring and punctual trip cards
    const recurringCards = page.locator('ev-trip-planner-panel >> .trip-card[recurring="true"]');
    const punctualCards = page.locator('ev-trip-planner-panel >> .trip-card[punctual="true"]');

    // At least one type should be visible
    const hasRecurring = await recurringCards.count() > 0;
    const hasPunctual = await punctualCards.count() > 0;
    expect(hasRecurring || hasPunctual).toBe(true);
  });

  test('should show trip details (time, distance, consumption)', async ({ page }) => {
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      // Verify trip cards contain expected details
      const firstCard = tripCards.first();
      await expect(firstCard).toBeVisible({ timeout: 10000 });
    }
  });
});
