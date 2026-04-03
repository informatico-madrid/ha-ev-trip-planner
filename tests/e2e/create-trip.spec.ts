/**
 * E2E Test: Create Trip Flow
 *
 * Purpose: Verifies that users can successfully create a new trip with valid data
 * in the EV Trip Planner panel. Tests the complete trip creation flow including
 * navigation, form interaction, and validation of the created trip.
 *
 * Expected values:
 *   - km: 50 (distance traveled)
 *   - kwh: 15 (energy consumed)
 *   - tripType: puntual (one-time trip)
 *   - description: "Test Commute"
 */
import { test, expect, type Page } from '@playwright/test';
import { deleteTestTrip, type TripData } from './trips-helpers';

/**
 * Trip creation test data
 * km=50 and kwh=15 are the expected values used for form input and assertions
 */
const testTripData: TripData = {
  tripType: 'puntual',
  datetime: '2026-04-15T08:30',
  km: 50,       // Expected distance: 50 km
  kwh: 15,      // Expected energy: 15 kWh
  description: 'Test Commute',
};

test.describe('Create Trip', () => {
  test('should create a new trip with valid data', async ({ page }: { page: Page }) => {
    // Step 1: Navigate to the Home Assistant home page
    await page.goto('/');
    await page.waitForURL('/home');

    // Step 2: Navigate to EV Trip Planner panel via sidebar
    await page.getByRole('link', { name: 'EV Trip Planner' }).click();
    await page.waitForURL(/\/ev_trip_planner\//);

    // Step 3: Open the trip creation form by clicking "+ Agregar Viaje" button
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Step 4: Select trip type as "puntual" (one-time trip) using combobox
    await page.getByRole('combobox').selectOption(testTripData.tripType);

    // Step 5: Fill in the trip form fields with test data (km=50, kwh=15)
    // Fill datetime field with ISO format: 2026-04-15T08:30
    await page.getByLabel(/datetime/i).fill(testTripData.datetime);
    // Fill distance: 50 km
    await page.getByLabel(/km/i).fill(String(testTripData.km));
    // Fill energy consumption: 15 kWh
    await page.getByLabel(/kwh/i).fill(String(testTripData.kwh));
    // Fill trip description
    await page.getByLabel(/descripci/i).fill(testTripData.description);

    // Step 6: Submit the form by clicking "Crear Viaje" button
    await page.getByRole('button', { name: 'Crear Viaje' }).click();

    // Step 7: Verify the trip appears in the trips list after creation
    const tripCard = page.locator('.trip-card').filter({ hasText: testTripData.description });
    await expect(tripCard).toBeVisible();

    // Step 8: Verify the trip values match expected values (km=50, kwh=15)
    await expect(tripCard.getByText(String(testTripData.km))).toBeVisible();
    await expect(tripCard.getByText(String(testTripData.kwh))).toBeVisible();
    await expect(tripCard.getByText(testTripData.description)).toBeVisible();

    // Step 9: Clean up - delete the created trip after test completes
    const tripId = `${testTripData.datetime}-${testTripData.description}`;
    await deleteTestTrip(page, tripId);
  });
});