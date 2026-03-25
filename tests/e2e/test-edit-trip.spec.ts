/**
 * E2E Test: Edit Trip (Complete CRUD Validation)
 *
 * Verifies that editing a trip actually updates the backend, not just the UI.
 *
 * Usage:
 *   npx playwright test test-edit-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Edit Trip - Complete Validation', () => {
  // Helper to fetch trips from backend
  async function fetchTripsFromBackend(page: any, vehicle: string) {
    const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
      data: { service_data: { vehicle_id: vehicle } }
    });
    return await response.json();
  }

  test('should edit a recurring trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip data from backend
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialRecurringTrips = initialResponse?.result?.recurring_trips || [];

    if (initialRecurringTrips.length === 0) {
      test.skip('No recurring trips to edit');
      return;
    }

    // Get the first trip ID
    const tripId = initialRecurringTrips[0].id;
    const originalTime = initialRecurringTrips[0].hora;
    const originalKm = initialRecurringTrips[0].km;

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Verify form is pre-filled with original data
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    const tripTime = page.locator('ev-trip-planner-panel >> #trip-time');
    const tripKm = page.locator('ev-trip-planner-panel >> #trip-km');

    await expect(tripTime).toHaveValue(originalTime);
    await expect(tripKm).toHaveValue(String(originalKm));

    // Modify the trip
    const newTime = '15:30';
    const newKm = '35.0';

    await tripTime.fill(newTime);
    await tripKm.fill(newKm);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend was actually updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrips = updatedResponse?.result?.recurring_trips || [];

    const updatedTrip = updatedTrips.find((t: any) => t.id === tripId);

    expect(updatedTrip).toBeDefined('Trip should exist in backend after edit');
    expect(updatedTrip.hora).toBe(newTime, 'Backend should have updated time');
    expect(updatedTrip.km).toBe(parseFloat(newKm), 'Backend should have updated km');

    // Verify UI reflects the backend state
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await expect(tripCard).toContainText(newTime);
    await expect(tripCard).toContainText(`${newKm} km`);
  });

  test('should edit trip description and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const tripId = initialResponse?.result?.recurring_trips?.[0]?.id;

    if (!tripId) {
      test.skip('No trips to edit');
      return;
    }

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Get original description
    const originalDesc = await page.locator('ev-trip-planner-panel >> #trip-description').inputValue();

    // Update description
    const newDesc = 'Updated description from E2E test';
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(newDesc);

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend was updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrip = updatedResponse.result.recurring_trips.find((t: any) => t.id === tripId);

    expect(updatedTrip.descripcion).toBe(newDesc, 'Backend should have updated description');
  });

  test('should edit trip day and time and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const tripId = initialResponse?.result?.recurring_trips?.[0]?.id;

    if (!tripId) {
      test.skip('No trips to edit');
      return;
    }

    const originalDay = initialResponse.result.recurring_trips[0].dia_semana;
    const originalTime = initialResponse.result.recurring_trips[0].hora;

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Change day and time
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('5'); // Friday
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('18:00');

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend was updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrip = updatedResponse.result.recurring_trips.find((t: any) => t.id === tripId);

    expect(updatedTrip.dia_semana).toBe('5', 'Backend should have updated day to Friday');
    expect(updatedTrip.hora).toBe('18:00', 'Backend should have updated time');
  });

  test('should verify edit fails with invalid data - backend unchanged', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const tripId = initialResponse?.result?.recurring_trips?.[0]?.id;
    const originalKm = initialResponse?.result?.recurring_trips?.[0]?.km;

    if (!tripId) {
      test.skip('No trips to edit');
      return;
    }

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Set invalid data (empty km)
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('');

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Check backend - should be unchanged
    const response = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrip = response.result.recurring_trips.find((t: any) => t.id === tripId);

    expect(updatedTrip.km).toBe(originalKm, 'Backend should reject edit with invalid data');
  });

  test('should edit a punctual trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualTrips = initialResponse?.result?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to edit');
      return;
    }

    const tripId = initialPunctualTrips[0].id;
    const originalDatetime = initialPunctualTrips[0].datetime;

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Change datetime
    const newDatetime = '2026-04-15T20:00';
    await page.locator('ev-trip-planner-panel >> #trip-datetime').fill(newDatetime);

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend was updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrip = updatedResponse.result.punctual_trips.find((t: any) => t.id === tripId);

    expect(updatedTrip.datetime).toBe(newDatetime, 'Backend should have updated datetime');
  });
});
