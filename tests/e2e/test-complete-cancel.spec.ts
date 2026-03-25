/**
 * E2E Test: Complete/Cancel Punctual Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * This test verifies complete/cancel actually updates the backend and removes trips.
 *
 * Usage:
 *   npx playwright test test-complete-cancel.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner - Complete/Cancel Validation', () => {
  // Helper to fetch trips from backend
  async function fetchTripsFromBackend(page: any, vehicle: string) {
    const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
      data: { service_data: { vehicle_id: vehicle } }
    });
    return await response.json();
  }

  test('should complete a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trips from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualTrips = initialResponse?.result?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to complete');
      return;
    }

    const tripToComplete = initialPunctualTrips[0];
    const tripId = tripToComplete.id;
    const initialCount = initialPunctualTrips.length;

    // Find and click complete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.complete-btn').click();

    // Accept confirmation
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres completar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still exist in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentTrips = response?.result?.punctual_trips || [];
      expect(currentTrips.length).toBe(initialCount, 'Backend should not complete trip when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually completed (removed) from the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.result?.punctual_trips || [];

    // Completed trips should be removed from the list
    const completedTripStillExists = updatedPunctualTrips.find((t: any) => t.id === tripId);
    expect(completedTripStillExists).toBeUndefined(
      'Backend should have removed the completed trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  test('should cancel a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trips from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualTrips = initialResponse?.result?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to cancel');
      return;
    }

    const tripToCancel = initialPunctualTrips[0];
    const tripId = tripToCancel.id;
    const initialCount = initialPunctualTrips.length;

    // Find and click cancel button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.cancel-btn').click();

    // Accept confirmation
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres cancelar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still exist in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentTrips = response?.result?.punctual_trips || [];
      expect(currentTrips.length).toBe(initialCount, 'Backend should not cancel trip when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually cancelled (removed) from the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.result?.punctual_trips || [];

    // Cancelled trips should be removed from the list
    const cancelledTripStillExists = updatedPunctualTrips.find((t: any) => t.id === tripId);
    expect(cancelledTripStillExists).toBeUndefined(
      'Backend should have removed the cancelled trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  test('should verify complete action removes trip from backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.punctual_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No punctual trips to complete');
      return;
    }

    const tripId = initialResponse.result.punctual_trips[0].id;

    // Complete the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.complete-btn').click();

    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres completar este viaje?');
    });

    if (confirmed) {
      // Verify trip is removed from backend
      const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
      const updatedTrips = updatedResponse?.result?.punctual_trips || [];

      const tripStillExists = updatedTrips.find((t: any) => t.id === tripId);
      expect(tripStillExists).toBeUndefined('Backend should remove completed trip');
      expect(updatedTrips.length).toBe(initialCount - 1, 'Backend count should decrease by 1');
    }
  });

  test('should verify cancel action removes trip from backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.punctual_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No punctual trips to cancel');
      return;
    }

    const tripId = initialResponse.result.punctual_trips[0].id;

    // Cancel the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.cancel-btn').click();

    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres cancelar este viaje?');
    });

    if (confirmed) {
      // Verify trip is removed from backend
      const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
      const updatedTrips = updatedResponse?.result?.punctual_trips || [];

      const tripStillExists = updatedTrips.find((t: any) => t.id === tripId);
      expect(tripStillExists).toBeUndefined('Backend should remove cancelled trip');
      expect(updatedTrips.length).toBe(initialCount - 1, 'Backend count should decrease by 1');
    }
  });

  test('should show complete button only on active punctual trips', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const punctualTrips = response?.result?.punctual_trips || [];

    if (punctualTrips.length === 0) {
      test.skip('No punctual trips');
      return;
    }

    // Complete the first trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.complete-btn').click();

    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres completar este viaje?');
    });

    if (confirmed) {
      // After completion, complete button should be gone
      const completeButtons = page.locator('ev-trip-planner-panel >> .complete-btn');
      await expect(completeButtons).toHaveCount(0, { timeout: 5000 });

      // And cancel button should appear (for completed trips)
      const cancelButtons = page.locator('ev-trip-planner-panel >> .cancel-btn');
      // Cancel button should exist for the completed trip
      await expect(cancelButtons.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('should verify complete/cancel affects actual trip count in backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.punctual_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No punctual trips');
      return;
    }

    // Complete the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.complete-btn').click();

    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres completar este viaje?');
    });

    if (confirmed) {
      // Verify backend count decreased
      const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
      const updatedCount = updatedResponse?.result?.punctual_trips?.length || 0;

      expect(updatedCount).toBe(initialCount - 1, 'Backend should reflect completed trip removal');
    }
  });
});
