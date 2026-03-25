/**
 * E2E Test: Create Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * A test that only checks if the form closed is USELESS - the backend might have failed.
 *
 * Usage:
 *   npx playwright test test-create-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner - Complete Trip Creation Validation', () => {
  // Helper to fetch trips from backend
  async function fetchTripsFromBackend(page: any, vehicle: string) {
    const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
      data: { service_data: { vehicle_id: vehicle } }
    });
    return await response.json();
  }

  test('should create a recurring trip and verify it exists in backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with recurring trip data
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1'); // Monday
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('09:30');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.2');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test recurring trip from E2E');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually created in the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedCount = updatedResponse?.result?.recurring_trips?.length || 0;

    // Backend MUST have created at least 1 new trip
    expect(updatedCount).toBeGreaterThan(initialCount,
      'Backend should have created a new recurring trip');

    // Verify the new trip has the correct data
    const newTrip = updatedResponse.result.recurring_trips.find(
      (t: any) => t.descripcion === 'Test recurring trip from E2E'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.dia_semana).toBe('1', 'Day should be Monday');
    expect(newTrip.hora).toBe('09:30', 'Time should be 09:30');
    expect(newTrip.km).toBe(25.5, 'Distance should be 25.5 km');

    // Verify UI reflects the backend state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedCount, { timeout: 10000 });
  });

  test('should create a punctual trip and verify it exists in backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualCount = initialResponse?.result?.punctual_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with punctual trip data
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
    await page.locator('ev-trip-planner-panel >> #trip-datetime').fill('2026-03-25T14:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('15.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('3.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Punctual trip to airport');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually created in the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualCount = updatedResponse?.result?.punctual_trips?.length || 0;

    // Backend MUST have created at least 1 new punctual trip
    expect(updatedPunctualCount).toBeGreaterThan(initialPunctualCount,
      'Backend should have created a new punctual trip');

    // Verify the new trip has the correct data
    const newTrip = updatedResponse.result.punctual_trips.find(
      (t: any) => t.descripcion === 'Punctual trip to airport'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.datetime).toContain('2026-03-25', 'Date should be 2026-03-25');
    expect(newTrip.datetime).toContain('14:00', 'Time should be 14:00');

    // Verify UI reflects the backend state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const totalTrips = updatedResponse.result.recurring_trips.length + updatedPunctualCount;
    await expect(tripCards).toHaveCount(totalTrips, { timeout: 10000 });
  });

  test('should validate required fields - empty km should fail', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with EMPTY required fields (km should be required)
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill(''); // Empty - should fail
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.0');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Backend should reject the invalid trip - count should be unchanged
    const response = await fetchTripsFromBackend(page, vehicleId);
    const currentCount = response?.result?.recurring_trips?.length || 0;

    // The backend should NOT have created a trip with empty km
    expect(currentCount).toBe(initialCount,
      'Backend should reject trip with empty required field');
  });

  test('should create trip with special characters and verify backend storage', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with special characters in description
    const specialChars = 'Test with special: á é í ó ú ñ <script>alert("xss")</script>';
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('2.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(specialChars);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend stored the description correctly (escaped)
    const response = await fetchTripsFromBackend(page, vehicleId);
    const newTrip = response.result.recurring_trips.find(
      (t: any) => t.descripcion && t.descripcion.includes('special')
    );

    expect(newTrip).toBeDefined('Trip with special characters should be stored in backend');

    // Backend should have escaped the HTML (XSS protection)
    expect(newTrip.descripcion).not.toContain('<script>');
  });

  test('should handle long descriptions', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with very long description
    const longDescription = 'A'.repeat(2000);
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('2.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(longDescription);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend stored the long description
    const response = await fetchTripsFromBackend(page, vehicleId);
    const newTrip = response.result.recurring_trips.find(
      (t: any) => t.descripcion && t.descripcion.length > 100
    );

    expect(newTrip).toBeDefined('Trip with long description should be stored in backend');
    expect(newTrip.descripcion.length).toBeGreaterThan(100, 'Backend should store long description');
  });
});
