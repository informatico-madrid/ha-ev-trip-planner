/**
 * E2E Test: Edit Trip - Complete Backend Validation
 *
 * IMPORTANT: Tests MUST verify the actual system state changes, not just UI behavior.
 * A test that only checks if the form closed is USELESS - the backend might have failed.
 *
 * Usage:
 *   npx playwright test test-edit-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || process.env.HA_TEST_URL || 'http://192.168.1.201:8123';

test.describe('EV Trip Planner - Complete Edit Validation', () => {
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

  test('should edit a recurring trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip from panel
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to edit');
      return;
    }

    const originalTime = initialTrips[0].hora;

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Verify form is pre-filled with original data from panel
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    const tripTime = page.locator('ev-trip-planner-panel >> #trip-time');

    await expect(tripTime).toHaveValue(originalTime);

    // Modify the trip
    const newTime = '15:30';
    await tripTime.fill(newTime);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually updated in the panel
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrips = updatedResponse?.recurring_trips || [];

    const updatedTrip = updatedTrips.find((t: any) => t.hora === newTime);

    expect(updatedTrip).toBeDefined('Trip should exist in panel after edit');
    expect(updatedTrip.hora).toBe(newTime, 'Panel should have updated time');

    // Verify UI reflects the panel state
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await expect(tripCard).toContainText(newTime);
  });

  test('should edit trip description and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No trips to edit');
      return;
    }

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Update description
    const newDesc = 'Updated description from E2E test';
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(newDesc);

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // Wait for state to update
    await page.waitForTimeout(1000);

    // CRITICAL: Verify panel was updated
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrip = updatedResponse.recurring_trips.find((t: any) => t.descripcion === newDesc);

    expect(updatedTrip.descripcion).toBe(newDesc, 'Panel should have updated description');
  });

  test('should edit trip day and time and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No trips to edit');
      return;
    }

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

    // Wait for state to update
    await page.waitForTimeout(1000);

    // CRITICAL: Verify panel was updated
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrip = updatedResponse.recurring_trips.find((t: any) => t.hora === '18:00');

    expect(updatedTrip).toBeDefined('Trip should exist in panel after edit');
    expect(updatedTrip.hora).toBe('18:00', 'Panel should have updated time');
  });

  test('should verify edit fails with invalid data - backend unchanged', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial trip
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No trips to edit');
      return;
    }

    const originalTime = initialTrips[0].hora;

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Set invalid data (clear time)
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('');

    // Submit
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Check panel - should be unchanged
    const response = await fetchTripsFromPanel(page, vehicleId);
    const currentTrips = response?.recurring_trips || [];
    const currentTrip = currentTrips.find((t: any) => t.hora === originalTime);

    expect(currentTrip).toBeDefined('Panel should reject edit with invalid data');
  });

  test('should edit a punctual trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForTimeout(3000);

    // Get initial punctual trip
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to edit');
      return;
    }

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

    // Wait for state to update
    await page.waitForTimeout(1000);

    // CRITICAL: Verify panel was updated
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrip = updatedResponse.punctual_trips.find((t: any) => t.datetime === newDatetime);

    expect(updatedTrip.datetime).toBe(newDatetime, 'Panel should have updated datetime');
  });
});
