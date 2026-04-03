/**
 * E2E Test: Complete and Cancel Punctual Trip
 *
 * User Stories:
 * - As a user, I want to mark a puntual trip as complete when it's done
 * - As a user, I want to cancel a puntual trip that I no longer need
 *
 * Both actions remove the trip from the list after confirmation.
 *
 * Flow (Complete):
 * 1. Create a puntual trip
 * 2. Click "✓ Completar" button
 * 3. Confirm the completion dialog
 * 4. Verify trip is removed from the list
 *
 * Flow (Cancel):
 * 1. Create a puntual trip
 * 2. Click "❌ Cancelar" button
 * 3. Confirm the cancellation dialog
 * 4. Verify trip is removed from the list
 */
import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, navigateToPanel, setupDialogHandler } from './trips-helpers';

test.describe('Complete and Cancel Punctual Trip', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
  });

  test('should complete a puntual trip and remove it from the list', async ({ page }: { page: Page }) => {
    // Step 1: Create a puntual trip
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-12T16:00',
      60,
      18,
      'Complete Test Trip',
    );

    // Step 2: Find the trip card
    const tripCard = page.locator('.trip-card', { hasText: 'Complete Test Trip' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Verify the "✓ Completar" button is visible (puntual-specific)
    await expect(tripCard.getByText('Completar')).toBeVisible();

    // Step 4: Set up confirm dialog handler and click Complete
    const confirmPromise = setupDialogHandler(page, true);
    await tripCard.getByText('Completar').click();

    // Step 5: Verify confirm dialog
    const confirmMsg = await confirmPromise;
    expect(confirmMsg).toContain('¿Estás seguro de que quieres completar este viaje?');

    // Step 6: Handle the success alert
    const alertPromise = setupDialogHandler(page, true);
    const alertMsg = await alertPromise;
    expect(alertMsg).toContain('Viaje completado');

    // Step 7: Verify trip is no longer in the list
    await expect(page.getByText('Complete Test Trip')).toBeHidden();
  });

  test('should cancel a puntual trip and remove it from the list', async ({ page }: { page: Page }) => {
    // Step 1: Create a puntual trip
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-13T10:00',
      35,
      10,
      'Cancel Trip Test',
    );

    // Step 2: Find the trip card
    const tripCard = page.locator('.trip-card', { hasText: 'Cancel Trip Test' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Verify the "❌ Cancelar" button is visible (puntual-specific)
    // Note: The form also has a "Cancelar" button, so we need to be specific
    await expect(tripCard.locator('.cancel-btn')).toBeVisible();

    // Step 4: Set up confirm dialog handler and click Cancel (the trip action, not form cancel)
    const confirmPromise = setupDialogHandler(page, true);
    await tripCard.locator('.cancel-btn').click();

    // Step 5: Verify confirm dialog
    const confirmMsg = await confirmPromise;
    expect(confirmMsg).toContain('¿Estás seguro de que quieres cancelar este viaje?');

    // Step 6: Handle the success alert
    const alertPromise = setupDialogHandler(page, true);
    const alertMsg = await alertPromise;
    expect(alertMsg).toContain('Viaje cancelado');

    // Step 7: Verify trip is no longer in the list
    await expect(page.getByText('Cancel Trip Test')).toBeHidden();
  });

  test('should dismiss complete dialog and keep trip', async ({ page }: { page: Page }) => {
    // Step 1: Create a puntual trip
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-14T12:00',
      28,
      8,
      'Dismiss Complete Test',
    );

    // Step 2: Find the trip card
    const tripCard = page.locator('.trip-card', { hasText: 'Dismiss Complete Test' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Set up dialog to DISMISS (cancel the completion)
    const confirmPromise = setupDialogHandler(page, false);

    // Step 4: Click Complete button
    await tripCard.getByText('Completar').click();

    // Step 5: Verify dialog was shown
    const confirmMsg = await confirmPromise;
    expect(confirmMsg).toContain('¿Estás seguro de que quieres completar este viaje?');

    // Step 6: Trip should still be visible
    await expect(page.getByText('Dismiss Complete Test')).toBeVisible();

    // Step 7: Clean up - actually delete the trip
    const deleteConfirmPromise = setupDialogHandler(page, true);
    await tripCard.getByText('Eliminar').click();
    await deleteConfirmPromise;
    const alertPromise = setupDialogHandler(page, true);
    await alertPromise;
  });
});
