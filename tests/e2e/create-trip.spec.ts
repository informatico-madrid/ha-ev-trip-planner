/**
 * E2E Test: Create Trip Flow
 *
 * Covers two user stories:
 * - US-1: Create a puntual (one-time) trip with valid data
 * - Additional: Create a recurrente (recurring weekly) trip with valid data
 *
 * Both trip types verify the complete creation flow including navigation,
 * form interaction, and validation of the created trip in the list.
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, deleteTestTrip, setupAlertHandler, cleanupTestTrips } from './trips-helpers';

test.describe('Create Trip', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('should create a new puntual trip with valid data', async ({ page }: { page: Page }) => {
    // Step 1: Open the trip creation form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Step 2: Select trip type as "puntual" (one-time trip)
    await page.locator('#trip-type').selectOption('puntual');

    // Step 3: Fill in the form fields
    await page.locator('#trip-datetime').fill('2026-04-15T08:30');
    await page.locator('#trip-km').fill('50');
    await page.locator('#trip-kwh').fill('15');
    await page.locator('#trip-description').fill('Test Commute Puntual');

    // Step 4: Handle the success alert and submit the form
    const alertPromise = setupAlertHandler(page);
    await page.getByRole('button', { name: 'Crear Viaje' }).click();
    const alertMsg = await alertPromise;

    // Step 5: Verify success alert
    expect(alertMsg).toContain('Viaje creado exitosamente');

    // Step 6: Verify the trip appears in the trips list
    await expect(page.getByText('Test Commute Puntual')).toBeVisible();
    await expect(page.getByText('50 km')).toBeVisible();
    await expect(page.getByText('15 kWh')).toBeVisible();

    // Step 7: Verify trip type badge shows "Puntual"
    await expect(page.getByText('Puntual').first()).toBeVisible();

    // Step 8: Clean up - delete the created trip
    await deleteTestTrip(page, '2026-04-15T08:30-Test Commute Puntual');
  });

  test('should create a new recurrente trip with valid data', async ({ page }: { page: Page }) => {
    // Step 1: Open the trip creation form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Step 2: Trip type defaults to "recurrente", verify it
    const tripTypeSelect = page.locator('#trip-type');
    await expect(tripTypeSelect).toHaveValue('recurrente');

    // Step 3: Select day of week - Lunes (value "1")
    await page.locator('#trip-day').selectOption('1');

    // Step 4: Set time
    await page.locator('#trip-time').fill('07:30');

    // Step 5: Fill distance and energy
    await page.locator('#trip-km').fill('25');
    await page.locator('#trip-kwh').fill('5');
    await page.locator('#trip-description').fill('Test Commute Recurrente');

    // Step 6: Handle the success alert and submit
    const alertPromise = setupAlertHandler(page);
    await page.getByRole('button', { name: 'Crear Viaje' }).click();
    const alertMsg = await alertPromise;

    // Step 7: Verify success alert
    expect(alertMsg).toContain('Viaje creado exitosamente');

    // Step 8: Verify the trip appears in the trips list
    await expect(page.getByText('Test Commute Recurrente')).toBeVisible();
    await expect(page.getByText('25 km')).toBeVisible();
    await expect(page.getByText('5 kWh')).toBeVisible();

    // Step 9: Verify trip type badge shows "Recurrente"
    await expect(page.getByText('Recurrente').first()).toBeVisible();

    // Step 10: Clean up
    await deleteTestTrip(page, '2026-04-15T07:30-Test Commute Recurrente');
  });
});