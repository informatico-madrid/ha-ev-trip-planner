/**
 * E2E Test: Trip List Loading and Display
 *
 * Verifies that the EV Trip Planner panel correctly loads trips from
 * the trip_list service and displays them in the UI.
 *
 * Usage:
 *   npx playwright test test-trip-list.spec.ts
 */

import { test, expect } from '@playwright/test';

const HA_URL = 'http://192.168.1.100:18123';
const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner Trip List Loading', () => {

  /**
   * Test: Verify trips section is displayed
   */
  test('should display trips section', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify trips section exists
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });
  });

  /**
   * Test: Verify trips section header
   */
  test('should show trips header with correct text', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for trips header
    const tripsHeader = page.locator('ev-trip-planner-panel >> .trips-header');
    await expect(tripsHeader).toBeVisible({ timeout: 10000 });

    // Verify header contains expected text
    const headerText = await tripsHeader.textContent();
    expect(headerText).toContain('Viajes Programados');
  });

  /**
   * Test: Verify add trip button is visible
   */
  test('should show add trip button', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for add trip button
    const addTripButton = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripButton).toBeVisible({ timeout: 10000 });
  });

  /**
   * Test: Verify trips list structure when trips exist
   */
  test('should display trips list structure', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for trips list container
    const tripsList = page.locator('ev-trip-planner-panel >> .trips-list');
    // If there are trips, the list should be visible
    const isVisible = await tripsList.isVisible({ timeout: 5000 });
    expect(isVisible).toBe(true);
  });

  /**
   * Test: Verify trip cards have correct structure
   */
  test('should display trip cards with correct structure', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      // Verify first card has expected structure
      const firstCard = tripCards.first();

      // Check card class
      await expect(firstCard).toHaveClass(/trip-card/);

      // Check for trip type
      const hasTripType = await firstCard.locator('.trip-type').count() > 0;
      expect(hasTripType).toBe(true);

      // Check for trip info
      const hasTripInfo = await firstCard.locator('.trip-info').count() > 0;
      expect(hasTripInfo).toBe(true);

      // Check for trip actions
      const hasTripActions = await firstCard.locator('.trip-actions').count() > 0;
      expect(hasTripActions).toBe(true);
    }
  });

  /**
   * Test: Verify trip card content format
   */
  test('should display trip card with correct content format', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      const firstCard = tripCards.first();
      const cardText = await firstCard.textContent();

      // Verify card contains expected elements
      // Should contain trip type (Recurrente or Puntual)
      const hasTripType = cardText.includes('Recurrente') || cardText.includes('Puntual');
      expect(hasTripType).toBe(true);
    }
  });

  /**
   * Test: Verify no trips message when empty
   */
  test('should show no trips message when no trips exist', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for trips section
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // Check for either no trips message or trip cards
    const hasNoTrips = await page.locator('ev-trip-planner-panel >> .no-trips').count() > 0;
    const hasTripCards = await page.locator('ev-trip-planner-panel >> .trip-card').count() > 0;

    // Should have either no trips message or trip cards
    expect(hasNoTrips || hasTripCards).toBe(true);
  });

  /**
   * Test: Verify dynamic trip card rendering
   */
  test('should render dynamic trip card content', async ({ page }) => {
    await page.goto(`${HA_URL}/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      // Check that trip cards contain dynamic content
      const firstCard = tripCards.first();
      const cardText = await firstCard.textContent();

      // Verify card contains distance information
      const hasDistance = cardText.includes('km');
      expect(hasDistance).toBe(true);

      // Verify card contains time information if it's a recurring trip
      const hasTime = cardText.includes(':') || cardText.includes('Lunes') || cardText.includes('Martes') ||
                      cardText.includes('Miércoles') || cardText.includes('Jueves') || cardText.includes('Viernes') ||
                      cardText.includes('Sábado') || cardText.includes('Domingo');
      expect(hasTime).toBe(true);
    }
  });
});
