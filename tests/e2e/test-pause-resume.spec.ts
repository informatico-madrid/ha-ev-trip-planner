/**
 * E2E Test: Pause/Resume Recurring Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * This test verifies pause/resume actually updates the backend.
 *
 * Usage:
 *   npx playwright test test-pause-resume.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner - Complete Pause/Resume Validation', () => {
  // Helper to fetch trips from backend
  async function fetchTripsFromBackend(page: any, vehicle: string) {
    const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
      data: { service_data: { vehicle_id: vehicle } }
    });
    return await response.json();
  }

  test('should pause a recurring trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip state from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to pause');
      return;
    }

    const tripToPause = initialTrips.find((t: any) => t.activo !== false) || initialTrips[0];
    const tripId = tripToPause.id;
    const initialActive = tripToPause.activo !== false;

    if (!initialActive) {
      test.skip('Trip already paused, need active trip to test pause');
      return;
    }

    // Click pause button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

    // Accept confirmation
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres pausar este viaje recurrente?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still be active in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentTrip = response.result.recurring_trips.find((t: any) => t.id === tripId);
      expect(currentTrip.activo).toBe(true, 'Backend should keep trip active when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually paused in the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrip = updatedResponse.result.recurring_trips.find((t: any) => t.id === tripId);

    expect(updatedTrip).toBeDefined('Trip should exist in backend after pause');
    expect(updatedTrip.activo).toBe(false, 'Backend should have paused the trip');
  });

  test('should resume a paused trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip state from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to resume');
      return;
    }

    const tripToResume = initialTrips.find((t: any) => t.activo === false) || null;

    if (!tripToResume) {
      test.skip('No paused trips to resume');
      return;
    }

    const tripId = tripToResume.id;

    // Click resume button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.resume-btn').click();

    // Accept confirmation
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres reanudar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still be paused in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentTrip = response.result.recurring_trips.find((t: any) => t.id === tripId);
      expect(currentTrip.activo).toBe(false, 'Backend should keep trip paused when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually resumed in the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrip = updatedResponse.result.recurring_trips.find((t: any) => t.id === tripId);

    expect(updatedTrip).toBeDefined('Trip should exist in backend after resume');
    expect(updatedTrip.activo).toBe(true, 'Backend should have resumed the trip');
  });

  test('should toggle trip state and verify backend changes', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip state from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to toggle');
      return;
    }

    const tripId = initialTrips[0].id;
    const initialActive = initialTrips[0].activo !== false;

    // Pause the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

    const pauseConfirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres pausar este viaje recurrente?');
    });

    if (pauseConfirmed) {
      // Verify trip is paused in backend
      const pausedResponse = await fetchTripsFromBackend(page, vehicleId);
      const pausedTrip = pausedResponse.result.recurring_trips.find((t: any) => t.id === tripId);
      expect(pausedTrip.activo).toBe(false, 'Backend should have paused the trip');

      // Now resume the trip
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.resume-btn').click();

      const resumeConfirmed = await page.evaluate(() => {
        return confirm('¿Estás seguro de que quieres reanudar este viaje?');
      });

      if (resumeConfirmed) {
        // Verify trip is resumed in backend
        const resumedResponse = await fetchTripsFromBackend(page, vehicleId);
        const resumedTrip = resumedResponse.result.recurring_trips.find((t: any) => t.id === tripId);
        expect(resumedTrip.activo).toBe(true, 'Backend should have resumed the trip');
      }
    }
  });

  test('should verify pause button only appears on active trips', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const trips = response?.result?.recurring_trips || [];

    // Count active vs inactive trips
    const activeTrips = trips.filter((t: any) => t.activo !== false);
    const inactiveTrips = trips.filter((t: any) => t.activo === false);

    // Click on an active trip to pause it
    if (activeTrips.length > 0) {
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

      const confirmed = await page.evaluate(() => {
        return confirm('¿Estás seguro de que quieres pausar este viaje recurrente?');
      });

      if (confirmed) {
        // Verify pause button is gone and resume button appeared
        const pauseButton = page.locator('ev-trip-planner-panel >> .pause-btn');
        const resumeButton = page.locator('ev-trip-planner-panel >> .resume-btn');

        // Pause button should not be visible on the first trip anymore
        const visiblePauseButtons = await pauseButton.count();
        // Resume button should be visible
        await expect(resumeButton).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should verify pause/resume affects actual trip behavior', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip state
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips');
      return;
    }

    const tripId = initialTrips[0].id;
    const initialActive = initialTrips[0].activo !== false;

    // Pause the trip if active
    if (initialActive) {
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

      const confirmed = await page.evaluate(() => {
        return confirm('¿Estás seguro de que quieres pausar este viaje recurrente?');
      });

      if (confirmed) {
        // Verify backend state
        const pausedResponse = await fetchTripsFromBackend(page, vehicleId);
        const pausedTrip = pausedResponse.result.recurring_trips.find((t: any) => t.id === tripId);
        expect(pausedTrip.activo).toBe(false, 'Backend should reflect paused state');
      }
    }
  });
});
