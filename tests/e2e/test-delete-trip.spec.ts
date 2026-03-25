/**
 * E2E Test: Delete Trip (Complete CRUD Validation)
 *
 * Verifies that deleting a trip actually removes it from the backend, not just the UI.
 * A test that only checks if the form closed is useless - the backend might have failed.
 *
 * Usage:
 *   npx playwright test test-delete-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Delete Trip - Complete Validation', () => {
  // Helper to fetch trips from backend
  async function fetchTripsFromBackend(page: any, vehicle: string) {
    const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
      data: { service_data: { vehicle_id: vehicle } }
    });
    return await response.json();
  }

  test('should delete a recurring trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count and ID from backend
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialRecurringTrips = initialResponse?.result?.recurring_trips || [];

    if (initialRecurringTrips.length === 0) {
      test.skip('No recurring trips to delete');
      return;
    }

    const tripToDelete = initialRecurringTrips[0];
    const tripId = tripToDelete.id;
    const initialCount = initialRecurringTrips.length;

    // Click delete button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // CRITICAL: Verify backend was actually updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrips = updatedResponse?.result?.recurring_trips || [];

    // Backend should have deleted the trip
    const deletedTripStillExists = updatedTrips.find((t: any) => t.id === tripId);
    expect(deletedTripStillExists).toBeUndefined(
      'Backend should have deleted the trip'
    );

    // Verify count decreased
    expect(updatedTrips.length).toBe(initialCount - 1,
      'Backend trip count should decrease by 1');

    // Verify UI reflects backend state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedTrips.length + (updatedResponse.result.punctual_trips?.length || 0),
      { timeout: 10000 });
  });

  test('should delete a punctual trip and verify backend removal', async ({ page }) => {
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
      test.skip('No punctual trips to delete');
      return;
    }

    const tripToDelete = initialPunctualTrips[0];
    const tripId = tripToDelete.id;
    const initialCount = initialPunctualTrips.length;

    // Find and click delete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.delete-btn').click();

    // CRITICAL: Verify backend was actually updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.result?.punctual_trips || [];

    // Backend should have deleted the trip
    const deletedTripStillExists = updatedPunctualTrips.find((t: any) => t.id === tripId);
    expect(deletedTripStillExists).toBeUndefined(
      'Backend should have deleted the punctual trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  test('should cancel deletion and verify backend unchanged', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No trips to delete');
      return;
    }

    // Click delete button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // Set up handler to cancel deletion
    page.on('dialog', async (dialog) => {
      console.log(`Cancelling deletion: ${dialog.message()}`);
      await dialog.dismiss();
    });

    // Verify trip still exists in backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const currentCount = response?.result?.recurring_trips?.length || 0;

    // Backend should be unchanged
    expect(currentCount).toBe(initialCount,
      'Backend should not delete trip when user cancels');
  });

  test('should delete all trips and verify empty backend state', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get all trips
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialRecurring = initialResponse?.result?.recurring_trips || [];
    const initialPunctual = initialResponse?.result?.punctual_trips || [];

    if (initialRecurring.length === 0 && initialPunctual.length === 0) {
      test.skip('No trips to delete');
      return;
    }

    // Delete all trips
    for (const trip of [...initialRecurring, ...initialPunctual]) {
      const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();

      if (await tripCard.count() > 0) {
        await tripCard.locator('.delete-btn').click();

        // Accept deletion
        const confirmed = await page.evaluate(() => {
          return confirm('¿Estás seguro de que quieres eliminar este viaje?');
        });

        if (!confirmed) {
          await page.locator('body').press('Escape');
        }

        // Wait for trip to be removed
        await expect(tripCard).not.toBeVisible({ timeout: 10000 });
      }
    }

    // CRITICAL: Verify backend is empty
    const finalResponse = await fetchTripsFromBackend(page, vehicleId);
    const finalRecurring = finalResponse?.result?.recurring_trips || [];
    const finalPunctual = finalResponse?.result?.punctual_trips || [];

    expect(finalRecurring.length).toBe(0,
      'Backend should have no recurring trips after deletion');
    expect(finalPunctual.length).toBe(0,
      'Backend should have no punctual trips after deletion');

    // Verify UI shows empty state
    const noTripsMessage = page.locator('ev-trip-planner-panel >> .no-trips');
    await expect(noTripsMessage).toBeVisible({ timeout: 10000 });
  });

  test('should verify trip ID in backend matches UI', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trip ID from backend
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No trips to verify');
      return;
    }

    const backendTripId = initialTrips[0].id;

    // Get trip ID from UI
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    const uiTripId = await tripCard.getAttribute('data-trip-id');

    // Verify IDs match
    expect(uiTripId).toBe(backendTripId,
      'UI trip ID should match backend trip ID');
  });
});
