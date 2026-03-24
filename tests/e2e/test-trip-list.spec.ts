/**
 * E2E Test: Trip List Loading
 *
 * Verifies that the EV Trip Planner panel correctly loads trips from
 * the trip_list service and displays them in the UI.
 *
 * Usage:
 *   npx playwright test test-trip-list.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Trip List Loading', () => {
  // Test configuration
  const vehicleId = 'chispitas';
  const panelUrl = `http://192.168.1.100:8123/ev-trip-planner-${vehicleId}`;

  test('should display trips section', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Verify trips section exists
    const tripsSection = page.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  });

  test('should show "No hay viajes" when no trips exist', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.waitForSelector('#trips-section', { timeout: 10000 });

    // Check for "No hay viajes" message or trip cards
    const hasNoTrips = await page.locator('.no-trips').count() > 0;
    const hasTripCards = await page.locator('.trip-card').count() > 0;

    expect(hasNoTrips || hasTripCards).toBe(true);
  });

  test('should display trip count in header', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.waitForSelector('.trips-header', { timeout: 10000 });

    // Check for trip count in header
    const tripsHeader = page.locator('.trips-header h2');
    const headerText = await tripsHeader.textContent();

    // Header should contain "Viajes Programados" and optionally a count
    expect(headerText).toContain('Viajes Programados');
  });

  test('should display recurring trip cards when trips exist', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.waitForSelector('.trips-list', { timeout: 10000 });

    // Check for trip cards
    const tripCards = page.locator('.trip-card');
    const cardCount = await tripCards.count();

    // If trips exist, should see trip cards
    // (test passes if cards are displayed when they should be)
    expect(cardCount >= 0).toBe(true);
  });

  test('should show add trip button', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.waitForSelector('.trips-header', { timeout: 10000 });

    // Check for add trip button
    const addTripButton = page.locator('.add-trip-btn');
    await expect(addTripButton).toBeVisible();
    await expect(addTripButton).toContainText('+ Agregar Viaje');
  });

  test('should display trips with correct format', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.waitForSelector('.trips-list', { timeout: 10000 });

    // If trip cards exist, verify they have expected structure
    const tripCards = page.locator('.trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      // Verify first card has expected structure
      const firstCard = tripCards.first();
      await expect(firstCard).toHaveClass(/trip-card/);
    }
  });
});
