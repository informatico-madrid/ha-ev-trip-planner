import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, deleteTestTrip, type TripData } from './trips-helpers';

test.describe('Edit Trip', () => {
  test('should edit an existing recurrente trip', async ({ page }: { page: Page }) => {
    // T025: Implement navigation and setup
    // Step 1: Navigate to Home Assistant home
    await page.goto('/');
    await page.waitForURL('/home');

    // Step 2: Navigate to EV Trip Planner panel via sidebar
    await page.getByRole('link', { name: 'EV Trip Planner' }).click();
    await page.waitForURL(/\/ev_trip_planner\//);

    // Step 3: Create a recurrente trip first (day: Tuesday, time: 09:00, km: 30, kwh: 10)
    const tripId = await createTestTrip(
      page,
      'recurrente',
      '2026-04-07T09:00', // Tuesday April 7, 2026 at 09:00
      30,
      10,
      'Recurrente Test Trip',
    );

    // T026: Implement edit flow
    // Step 1: Click edit button (pencil icon) on trip card
    const tripCard = page.locator('div').filter({ hasText: 'Recurrente Test Trip' }).last();
    await tripCard.waitFor({ state: 'visible' });
    await tripCard.getByRole('button', { name: /edit/i }).click();

    // Step 2: Wait for edit form to appear
    await page.waitForSelector('text=km');

    // Step 3: Modify km to 35
    await page.getByLabel(/km/i).fill('35');

    // Step 4: Modify description to "Updated Test Route"
    await page.getByLabel(/descripci/i).fill('Updated Test Route');

    // Step 5: Click "Guardar Cambios" button to submit
    await page.getByRole('button', { name: 'Guardar Cambios' }).click();

    // T027: Assert trip card shows updated km=35 after save
    await expect(tripCard.getByText(/35/)).toBeVisible();

    // T027: Assert trip card shows updated description="Updated Test Route"
    await expect(tripCard.getByText('Updated Test Route')).toBeVisible();

    // Clean up: delete the test trip after test
    await deleteTestTrip(page, tripId);
  });
});
