/**
 * Edit Trip E2E Test
 *
 * Purpose: Verifies the edit flow for existing trips.
 * Tests:
 *   1. Edit a recurrente trip - modify km and description
 *   2. Edit a puntual trip - modify distance and energy values
 *
 * These tests verify the complete edit workflow including opening the edit form,
 * modifying fields, saving changes, and verifying updated values in the trip card.
 */

import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip, setupAlertHandler, cleanupTestTrips } from './trips-helpers';

test.describe('Edit Trip', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('should edit an existing recurrente trip', async ({ page }: { page: Page }) => {
    // Step 1: Create a recurrente trip with initial values
    const tripId = await createTestTrip(
      page,
      'recurrente',
      '2026-04-07T09:00',
      30,
      10,
      'Recurrente Edit Test',
      { day: '2', time: '09:00' },  // Martes at 09:00
    );

    // Step 2: Find the trip card by description
    const tripCard = page.locator('.trip-card', { hasText: 'Recurrente Edit Test' }).last();
    await tripCard.waitFor({ state: 'visible' });

    // Step 3: Click the edit button (✏️ Editar)
    await tripCard.getByText('Editar').click();

    // Step 4: Wait for the edit form to appear
    await page.locator('#edit-trip-km').waitFor({ state: 'visible' });

    // Step 5: Modify km from 30 -> 35
    await page.locator('#edit-trip-km').fill('35');

    // Step 6: Modify description
    await page.locator('#edit-trip-description').fill('Updated Recurrente Route');

    // Step 7: Handle the success alert and submit
    const alertPromise = setupAlertHandler(page);
    await page.getByRole('button', { name: 'Guardar Cambios' }).click();
    const alertMsg = await alertPromise;

    // Step 8: Verify success alert
    expect(alertMsg).toContain('Viaje actualizado exitosamente');

    // Step 9: Verify the trip card shows updated values
    await expect(page.getByText('Updated Recurrente Route')).toBeVisible();
    await expect(page.getByText('35 km')).toBeVisible();

    // Step 10: Clean up
    await deleteTestTrip(page, '2026-04-07T09:00-Updated Recurrente Route');
  });

  test('should edit an existing puntual trip', async ({ page }: { page: Page }) => {
    // Step 1: Create a puntual trip with initial values
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-20T14:00',
      40,
      12,
      'Puntual Edit Test',
    );

    // Step 2: Find the trip card
    const tripCard = page.locator('.trip-card', { hasText: 'Puntual Edit Test' }).last();
    await tripCard.waitFor({ state: 'visible' });

    // Step 3: Click edit button
    await tripCard.getByText('Editar').click();

    // Step 4: Wait for edit form
    await page.locator('#edit-trip-km').waitFor({ state: 'visible' });

    // Step 5: Update distance and energy
    await page.locator('#edit-trip-km').fill('45');
    await page.locator('#edit-trip-kwh').fill('14');

    // Step 6: Handle alert and submit
    const alertPromise = setupAlertHandler(page);
    await page.getByRole('button', { name: 'Guardar Cambios' }).click();
    const alertMsg = await alertPromise;

    // Step 7: Verify success
    expect(alertMsg).toContain('Viaje actualizado exitosamente');

    // Step 8: Verify updated values
    await expect(page.getByText('45 km')).toBeVisible();
    await expect(page.getByText('14 kWh')).toBeVisible();

    // Step 9: Clean up
    await deleteTestTrip(page, '2026-04-20T14:00-Puntual Edit Test');
  });
});
