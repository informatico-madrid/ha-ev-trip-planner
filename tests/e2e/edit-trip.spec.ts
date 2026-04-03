/**
 * Edit Trip E2E Test
 *
 * Purpose: Verifies the edit flow for an existing recurrente trip.
 * Flow:
 *   1. Navigate to Home Assistant and open EV Trip Planner panel
 *   2. Create a recurrente trip with initial values: km=30, kwh=10
 *   3. Open the edit form and modify km from 30 -> 35 and description
 *   4. Save changes and assert the trip card reflects the updated values
 *   5. Clean up: delete the test trip
 *
 * Expected values:
 *   - Initial km: 30, Final km: 35 (km changes from 30 to 35)
 *   - Initial description: 'Recurrente Test Trip'
 *   - Updated description: 'Updated Test Route'
 */

import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, deleteTestTrip, type TripData } from './trips-helpers';

test.describe('Edit Trip', () => {
  test('should edit an existing recurrente trip', async ({ page }: { page: Page }) => {
    // Step 1: Navigate to Home Assistant home page (HA SPA entry point)
    await page.goto('/');
    await page.waitForURL('/home');

    // Step 2: Open EV Trip Planner panel via sidebar navigation
    await page.getByRole('link', { name: 'EV Trip Planner' }).click();
    await page.waitForURL(/\/ev_trip_planner\//);

    // Step 3: Create a recurrente trip with initial km=30, kwh=10
    // This trip will be edited in the subsequent steps
    const tripId = await createTestTrip(
      page,
      'recurrente',
      '2026-04-07T09:00', // Tuesday April 7, 2026 at 09:00
      30,                  // initial km value (will be changed to 35)
      10,                  // initial kwh value
      'Recurrente Test Trip',
    );

    // Step 4: Locate the trip card and click the edit (pencil) button
    const tripCard = page.getByText('Recurrente Test Trip').last();
    await tripCard.waitFor({ state: 'visible' });
    await tripCard.getByRole('button', { name: /edit/i }).click();

    // Step 5: Wait for the edit form to appear (form contains 'km' label)
    await page.waitForSelector('text=km');

    // Step 6: Modify km from 30 -> 35 (expected value change)
    await page.getByLabel(/km/i).fill('35');

    // Step 7: Modify description to 'Updated Test Route'
    await page.getByLabel(/descripci/i).fill('Updated Test Route');

    // Step 8: Submit the edit form via 'Guardar Cambios' button
    await page.getByRole('button', { name: 'Guardar Cambios' }).click();

    // Step 9: Assert the trip card shows the updated km value (35 instead of 30)
    await expect(tripCard.getByText(/35/)).toBeVisible();

    // Step 10: Assert the trip card shows the updated description
    await expect(tripCard.getByText('Updated Test Route')).toBeVisible();

    // Step 11: Clean up - delete the test trip after the test completes
    await deleteTestTrip(page, tripId);
  });
});
