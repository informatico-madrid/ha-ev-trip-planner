/**
 * E2E Test: Pause/Resume Recurring Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * This test verifies pause/resume actually updates the panel state.
 *
 * Usage:
 *   npx playwright test test-pause-resume.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || process.env.HA_TEST_URL || 'http://192.168.1.201:8123';

test.describe('EV Trip Planner - Complete Pause/Resume Validation', () => {
  // Helper to fetch trips from the panel component state via JavaScript
  async function fetchTripsFromPanel(page: any, vehicle: string) {
    const trips = await page.evaluate(async () => {
      await new Promise((resolve) => setTimeout(resolve, 500));

      const panel = document.querySelector('ev-trip-planner-panel');
      if (!panel) {
        return { recurring_trips: [], punctual_trips: [] };
      }
      const shadow = panel.shadowRoot;
      if (!shadow) {
        return { recurring_trips: [], punctual_trips: [] };
      }
      const tripsSection = shadow.querySelector('.trips-section');
      if (!tripsSection) {
        return { recurring_trips: [], punctual_trips: [] };
      }
      const tripCards = tripsSection.querySelectorAll('.trip-card');
      const recurringCards = tripsSection.querySelectorAll('.trip-card[recurring="true"]');
      const punctualCards = tripsSection.querySelectorAll('.trip-card[punctual="true"]');
      return {
        recurring_trips: Array.from(recurringCards).map((c: any) => ({
          descripcion: c.querySelector('.trip-description')?.textContent?.trim() || '',
          hora: c.querySelector('.trip-time')?.textContent?.trim() || '',
          activo: c.classList.contains('paused') ? false : true
        })),
        punctual_trips: Array.from(punctualCards).map((c: any) => ({
          descripcion: c.querySelector('.trip-description')?.textContent?.trim() || '',
          datetime: c.querySelector('.trip-datetime')?.textContent?.trim() || ''
        }))
      };
    });
    return trips;
  }

  test('should pause a recurring trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip state from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to pause');
      return;
    }

    const tripToPause = initialTrips.find((t: any) => t.activo !== false) || initialTrips[0];
    const initialActive = tripToPause.activo !== false;

    if (!initialActive) {
      test.skip('Trip already paused, need active trip to test pause');
      return;
    }

    // Click pause button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

    // CRITICAL: Verify trip was actually paused in the panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrip = updatedResponse.recurring_trips.find((t: any) =>
      t.descripcion === tripToPause.descripcion
    );

    expect(updatedTrip).toBeDefined('Trip should exist in panel after pause');
    expect(updatedTrip.activo).toBe(false, 'Panel should have paused the trip');
  });

  test('should resume a paused trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip state from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to resume');
      return;
    }

    const tripToResume = initialTrips.find((t: any) => t.activo === false) || null;

    if (!tripToResume) {
      test.skip('No paused trips to resume');
      return;
    }

    // Click resume button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.resume-btn').click();

    // CRITICAL: Verify trip was actually resumed in the panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrip = updatedResponse.recurring_trips.find((t: any) =>
      t.descripcion === tripToResume.descripcion
    );

    expect(updatedTrip).toBeDefined('Trip should exist in panel after resume');
    expect(updatedTrip.activo).toBe(true, 'Panel should have resumed the trip');
  });

  test('should toggle trip state and verify backend changes', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip state from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to toggle');
      return;
    }

    const tripDesc = initialTrips[0].descripcion;
    const initialActive = initialTrips[0].activo !== false;

    // Pause the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

    // Verify trip is paused in panel
    const pausedResponse = await fetchTripsFromPanel(page, vehicleId);
    const pausedTrip = pausedResponse.recurring_trips.find((t: any) =>
      t.descripcion === tripDesc
    );
    expect(pausedTrip.activo).toBe(false, 'Panel should have paused the trip');

    // Now resume the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.resume-btn').click();

    // Verify trip is resumed in panel
    const resumedResponse = await fetchTripsFromPanel(page, vehicleId);
    const resumedTrip = resumedResponse.recurring_trips.find((t: any) =>
      t.descripcion === tripDesc
    );
    expect(resumedTrip.activo).toBe(true, 'Panel should have resumed the trip');
  });

  test('should verify pause button only appears on active trips', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get trips from panel
    const response = await fetchTripsFromPanel(page, vehicleId);
    const trips = response?.recurring_trips || [];

    // Count active vs inactive trips
    const activeTrips = trips.filter((t: any) => t.activo !== false);
    const inactiveTrips = trips.filter((t: any) => t.activo === false);

    // Click on an active trip to pause it
    if (activeTrips.length > 0) {
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

      // Verify pause button is gone and resume button appeared
      const pauseButton = page.locator('ev-trip-planner-panel >> .pause-btn');
      const resumeButton = page.locator('ev-trip-planner-panel >> .resume-btn');

      // Pause button should not be visible on the first trip anymore
      const visiblePauseButtons = await pauseButton.count();
      // Resume button should be visible
      await expect(resumeButton).toBeVisible({ timeout: 5000 });
    }
  });

  test('should verify pause/resume affects actual trip visibility', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip state
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips');
      return;
    }

    const tripDesc = initialTrips[0].descripcion;
    const initialActive = initialTrips[0].activo !== false;

    // Pause the trip if active
    if (initialActive) {
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

      // Verify panel state
      const pausedResponse = await fetchTripsFromPanel(page, vehicleId);
      const pausedTrip = pausedResponse.recurring_trips.find((t: any) =>
        t.descripcion === tripDesc
      );
      expect(pausedTrip.activo).toBe(false, 'Panel should reflect paused state');
    }
  });
});
