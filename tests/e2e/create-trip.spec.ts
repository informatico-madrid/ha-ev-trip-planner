import { test, expect } from '@playwright/test';
import { deleteTestTrip } from './trips-helpers';

test.describe('Create Trip', () => {
  test('should create a new trip with valid data', async ({ page }) => {
    // Navigate to EV Trip Planner panel
    await page.goto('/');
    await page.waitForURL('/home');
    await page.getByRole('link', { name: 'EV Trip Planner' }).click();
    await page.waitForURL(/\/ev_trip_planner\//);

    // T020: Fill and submit trip form
    // Click "+ Agregar Viaje" button
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Select trip type "puntual" with combobox
    await page.getByRole('combobox').selectOption('puntual');

    // Fill form fields
    await page.getByLabel(/datetime/i).fill('2026-04-15T08:30');
    await page.getByLabel(/km/i).fill('50');
    await page.getByLabel(/kwh/i).fill('15');
    await page.getByLabel(/descripci/i).fill('Test Commute');

    // Click "Crear Viaje" button to submit
    await page.getByRole('button', { name: 'Crear Viaje' }).click();

    // T021: Assert trip appears in trips list after creation
    const tripCard = page.locator('.trip-card').filter({ hasText: 'Test Commute' });
    await expect(tripCard).toBeVisible();

    // Assert trip values match: km=50, kwh=15, description="Test Commute"
    await expect(tripCard.getByText(/50/)).toBeVisible();
    await expect(tripCard.getByText(/15/)).toBeVisible();
    await expect(tripCard.getByText('Test Commute')).toBeVisible();

    // Clean up: delete the created trip after test
    const tripId = '2026-04-15T08:30-Test Commute';
    await deleteTestTrip(page, tripId);
  });
});