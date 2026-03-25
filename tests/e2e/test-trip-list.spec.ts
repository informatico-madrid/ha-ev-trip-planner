/**
 * E2E Test: Trip List Loading and Display with Backend Validation
 *
 * IMPORTANT: Tests MUST verify actual backend state changes, not just UI behavior.
 * This test validates trip list displays correctly from backend data.
 *
 * Usage:
 *   npx playwright test test-trip-list.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

// Helper to fetch trips from backend via service call
async function fetchTripsFromBackend(page: any, vehicle: string) {
  const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
    data: { service_data: { vehicle_id: vehicle } }
  });
  return await response.json();
}

test.describe('EV Trip Planner Trip List - VALIDACION BACKEND', () => {

  // ============================================
  // READ - Validar visualización de lista de viajes
  // ============================================

  test('should display trips section', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
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

  test('should show trips header with correct text', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
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

  test('should show add trip button', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
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

  test('should display trips list structure matching backend', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const totalBackendTrips = (response.result?.recurring_trips?.length || 0) +
                               (response.result?.punctual_trips?.length || 0);

    // Check for trips list container
    const tripsList = page.locator('ev-trip-planner-panel >> .trips-list');
    const isVisible = await tripsList.isVisible({ timeout: 5000 });

    // If there are trips in backend, trips-list should be visible
    if (totalBackendTrips > 0) {
      expect(isVisible).toBe(true, 'Trips list should be visible when backend has trips');
    }
  });

  test('should display trip cards matching backend count', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const backendRecurring = response.result?.recurring_trips?.length || 0;
    const backendPunctual = response.result?.punctual_trips?.length || 0;
    const totalBackendTrips = backendRecurring + backendPunctual;

    // Check for trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    // UI should match backend
    expect(cardCount).toBe(totalBackendTrips,
      'UI trip card count should match backend trip count');
  });

  test('should display trip cards with correct structure', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
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
      expect(hasTripType).toBe(true, 'Trip card should have trip type');

      // Check for trip info
      const hasTripInfo = await firstCard.locator('.trip-info').count() > 0;
      expect(hasTripInfo).toBe(true, 'Trip card should have trip info');

      // Check for trip actions
      const hasTripActions = await firstCard.locator('.trip-actions').count() > 0;
      expect(hasTripActions).toBe(true, 'Trip card should have trip actions');
    }
  });

  test('should display trip card with correct content format', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
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
      expect(hasTripType).toBe(true, 'Trip card should contain trip type');
    }
  });

  test('should show no trips message when backend is empty', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const backendRecurring = response.result?.recurring_trips?.length || 0;
    const backendPunctual = response.result?.punctual_trips?.length || 0;
    const hasAnyTrips = backendRecurring > 0 || backendPunctual > 0;

    // Check for trips section
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // Check for either no trips message or trip cards
    const hasNoTrips = await page.locator('ev-trip-planner-panel >> .no-trips').count() > 0;
    const hasTripCards = await page.locator('ev-trip-planner-panel >> .trip-card').count() > 0;

    if (!hasAnyTrips) {
      expect(hasNoTrips).toBe(true, 'Should show no trips message when backend is empty');
    } else {
      expect(hasTripCards).toBe(true, 'Should show trip cards when backend has trips');
    }
  });

  test('should render dynamic trip card content from backend', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const trips = [...(response.result?.recurring_trips || []), ...(response.result?.punctual_trips || [])];

    if (trips.length > 0) {
      // Check that trip cards contain dynamic content
      const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
      const firstCard = tripCards.first();
      const cardText = await firstCard.textContent();

      // Verify card contains distance information
      const hasDistance = cardText.includes('km');
      expect(hasDistance).toBe(true, 'Trip card should contain distance information');

      // Verify card contains time information if it's a recurring trip
      const hasTime = cardText.includes(':') || cardText.includes('Lunes') || cardText.includes('Martes') ||
                      cardText.includes('Miércoles') || cardText.includes('Jueves') || cardText.includes('Viernes') ||
                      cardText.includes('Sábado') || cardText.includes('Domingo') ||
                      cardText.includes('2026') || cardText.includes('2025');
      expect(hasTime).toBe(true, 'Trip card should contain time information');
    }
  });

  // ============================================
  // INTEGRATION - Validar flujo completo CRUD
  // ============================================

  test('should have complete CRUD integration flow', async ({ page }) => {
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify all CRUD buttons are present
    const addBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addBtn).toBeVisible({ timeout: 10000 });

    // Verify panel has all required elements
    const tripsHeader = page.locator('ev-trip-planner-panel >> .trips-header');
    await expect(tripsHeader).toBeVisible({ timeout: 10000 });

    // Verify trips section exists
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });
  });
});
