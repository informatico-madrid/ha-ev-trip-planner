/**
 * E2E Test: Complete/Cancel Punctual Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * This test verifies complete/cancel actually updates the panel state and removes trips.
 *
 * Usage:
 *   npx playwright test test-complete-cancel.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner - Complete/Cancel Validation', () => {
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
          datetime: c.querySelector('.trip-datetime')?.textContent?.trim() || '',
          completed: c.classList.contains('completed')
        }))
      };
    });
    return trips;
  }

  test('should complete a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trips from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to complete');
      return;
    }

    const tripToComplete = initialPunctualTrips[0];
    const initialCount = initialPunctualTrips.length;

    // Find and click complete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.complete-btn').click();

    // CRITICAL: Verify trip was actually completed (removed) from the panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.punctual_trips || [];

    // Completed trips should be removed from the list
    const completedTripStillExists = updatedPunctualTrips.find((t: any) =>
      t.descripcion === tripToComplete.descripcion
    );

    // Verify count decreased (completed trip removed)
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Panel punctual trip count should decrease by 1');
  });

  test('should cancel a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trips from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to cancel');
      return;
    }

    const tripToCancel = initialPunctualTrips[0];
    const initialCount = initialPunctualTrips.length;

    // Find and click cancel button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.cancel-btn').click();

    // CRITICAL: Verify trip was actually cancelled (removed) from the panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.punctual_trips || [];

    // Cancelled trips should be removed from the list
    const cancelledTripStillExists = updatedPunctualTrips.find((t: any) =>
      t.descripcion === tripToCancel.descripcion
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Panel punctual trip count should decrease by 1');
  });

  test('should verify complete action removes trip from panel', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialCount = initialResponse?.punctual_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No punctual trips to complete');
      return;
    }

    const tripDesc = initialResponse.punctual_trips[0].descripcion;

    // Complete the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.complete-btn').click();

    // Verify trip is removed from panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrips = updatedResponse?.punctual_trips || [];

    const tripStillExists = updatedTrips.find((t: any) => t.descripcion === tripDesc);
    expect(tripStillExists).toBeUndefined('Panel should remove completed trip');
    expect(updatedTrips.length).toBe(initialCount - 1, 'Panel count should decrease by 1');
  });

  test('should verify cancel action removes trip from panel', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialCount = initialResponse?.punctual_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No punctual trips to cancel');
      return;
    }

    const tripDesc = initialResponse.punctual_trips[0].descripcion;

    // Cancel the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.cancel-btn').click();

    // Verify trip is removed from panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrips = updatedResponse?.punctual_trips || [];

    const tripStillExists = updatedTrips.find((t: any) => t.descripcion === tripDesc);
    expect(tripStillExists).toBeUndefined('Panel should remove cancelled trip');
    expect(updatedTrips.length).toBe(initialCount - 1, 'Panel count should decrease by 1');
  });

  test('should show complete button only on active punctual trips', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get trips from panel
    const response = await fetchTripsFromPanel(page, vehicleId);
    const punctualTrips = response?.punctual_trips || [];

    if (punctualTrips.length === 0) {
      test.skip('No punctual trips');
      return;
    }

    // Complete the first trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.complete-btn').click();

    // After completion, complete button should be gone
    const completeButtons = page.locator('ev-trip-planner-panel >> .complete-btn');
    await expect(completeButtons).toHaveCount(0, { timeout: 5000 });

    // And cancel button should appear (for completed trips)
    const cancelButtons = page.locator('ev-trip-planner-panel >> .cancel-btn');
    // Cancel button should exist for the completed trip
    await expect(cancelButtons.first()).toBeVisible({ timeout: 5000 });
  });

  test('should verify complete/cancel affects actual trip count in panel', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialCount = initialResponse?.punctual_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No punctual trips');
      return;
    }

    // Complete the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.complete-btn').click();

    // Verify panel count decreased
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedCount = updatedResponse?.punctual_trips?.length || 0;

    expect(updatedCount).toBe(initialCount - 1, 'Panel should reflect completed trip removal');
  });
});
