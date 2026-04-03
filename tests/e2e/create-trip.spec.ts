import { test, expect, type Page } from '@playwright/test';
import { deleteTestTrip, type TripData } from './trips-helpers';

/**
 * Trip creation test data
 */
const testTripData: TripData = {
  tripType: 'puntual',
  datetime: '2026-04-15T08:30',
  km: 50,
  kwh: 15,
  description: 'Test Commute',
};

test.describe('Create Trip', () => {
  test('should create a new trip with valid data', async ({ page }: { page: Page }) => {
    // Navigate to EV Trip Planner panel
    await page.goto('/');
    await page.waitForURL('/home');
    await page.getByRole('link', { name: 'EV Trip Planner' }).click();
    await page.waitForURL(/\/ev_trip_planner\//);

    // T020: Fill and submit trip form
    // Click "+ Agregar Viaje" button
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Select trip type with combobox
    await page.getByRole('combobox').selectOption(testTripData.tripType);

    // Fill form fields
    await page.getByLabel(/datetime/i).fill(testTripData.datetime);
    await page.getByLabel(/km/i).fill(String(testTripData.km));
    await page.getByLabel(/kwh/i).fill(String(testTripData.kwh));
    await page.getByLabel(/descripci/i).fill(testTripData.description);

    // Click "Crear Viaje" button to submit
    await page.getByRole('button', { name: 'Crear Viaje' }).click();

    // T021: Assert trip appears in trips list after creation
    const tripCard = page.locator('.trip-card').filter({ hasText: testTripData.description });
    await expect(tripCard).toBeVisible();

    // Assert trip values match
    await expect(tripCard.getByText(String(testTripData.km))).toBeVisible();
    await expect(tripCard.getByText(String(testTripData.kwh))).toBeVisible();
    await expect(tripCard.getByText(testTripData.description)).toBeVisible();

    // Clean up: delete the created trip after test
    const tripId = `${testTripData.datetime}-${testTripData.description}`;
    await deleteTestTrip(page, tripId);
  });
});