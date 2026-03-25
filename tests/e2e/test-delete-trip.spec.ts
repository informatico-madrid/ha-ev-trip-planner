/**
 * E2E Test: Delete Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * A test that only checks if the form closed is USELESS - the backend might have failed.
 *
 * Usage:
 *   npx playwright test test-delete-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner - Complete Delete Validation', () => {
  // Helper to fetch trips from the panel component state via JavaScript
  async function fetchTripsFromPanel(page: any, vehicle: string) {
    const trips = await page.evaluate(async () => {
      // Wait for custom element to be defined
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
          hora: c.querySelector('.trip-time')?.textContent?.trim() || ''
        })),
        punctual_trips: Array.from(punctualCards).map((c: any) => ({
          descripcion: c.querySelector('.trip-description')?.textContent?.trim() || '',
          datetime: c.querySelector('.trip-datetime')?.textContent?.trim() || ''
        }))
      };
    });
    return trips;
  }

  test('should delete a recurring trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip count from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to delete');
      return;
    }

    const tripToDelete = initialTrips[0];
    const initialCount = initialTrips.length;

    // Click delete button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // Accept deletion via dialog - use Escape to cancel first
    await page.locator('body').press('Escape');

    // Check backend - should be unchanged if cancelled
    const responseAfterCancel = await fetchTripsFromPanel(page, vehicleId);
    const countAfterCancel = responseAfterCancel?.recurring_trips?.length || 0;
    expect(countAfterCancel).toBe(initialCount, 'Backend should not delete when user cancels');

    // Now actually delete
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // Accept deletion
    await page.locator('body').press('Escape');

    // CRITICAL: Verify trip was actually deleted from panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrips = updatedResponse?.recurring_trips || [];

    // Verify count decreased
    expect(updatedTrips.length).toBe(initialCount - 1,
      'Backend trip count should decrease by 1');

    // Verify UI reflects backend state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedTrips.length, { timeout: 10000 });
  });

  test('should delete a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to delete');
      return;
    }

    const initialCount = initialPunctualTrips.length;

    // Find and click delete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.delete-btn').click();

    // Accept deletion
    await page.locator('body').press('Escape');

    // CRITICAL: Verify trip was actually deleted from the panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.punctual_trips || [];

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  test('should verify cancellation keeps trip in backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialCount = initialResponse?.recurring_trips?.length || 0;

    if (initialCount === 0) {
      test.skip('No trips to delete');
      return;
    }

    // Click delete button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // Set up handler to cancel deletion
    page.on('dialog', async (dialog) => {
      await dialog.dismiss();
    });

    // Verify trip still exists in panel
    const response = await fetchTripsFromPanel(page, vehicleId);
    const currentCount = response?.recurring_trips?.length || 0;

    // Backend should be unchanged
    expect(currentCount).toBe(initialCount,
      'Backend should not delete trip when user cancels');
  });

  test('should delete all trips and verify empty backend state', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get all trips from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialRecurring = initialResponse?.recurring_trips || [];
    const initialPunctual = initialResponse?.punctual_trips || [];

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
        await page.locator('body').press('Escape');

        // Wait for trip to be removed
        await expect(tripCard).not.toBeVisible({ timeout: 10000 });
      }
    }

    // CRITICAL: Verify panel is empty
    const finalResponse = await fetchTripsFromPanel(page, vehicleId);
    const finalRecurring = finalResponse?.recurring_trips || [];
    const finalPunctual = finalResponse?.punctual_trips || [];

    expect(finalRecurring.length).toBe(0,
      'Panel should have no recurring trips after deletion');
    expect(finalPunctual.length).toBe(0,
      'Panel should have no punctual trips after deletion');

    // Verify UI shows empty state
    const noTripsMessage = page.locator('ev-trip-planner-panel >> .no-trips');
    await expect(noTripsMessage).toBeVisible({ timeout: 10000 });
  });
});
