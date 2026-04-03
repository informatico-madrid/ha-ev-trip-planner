/**
 * E2E Test: Pause and Resume Recurring Trip
 *
 * User Stories:
 * - As a user, I want to pause a recurring trip so it stops being scheduled
 * - As a user, I want to resume a paused recurring trip so it starts scheduling again
 *
 * Flow:
 * 1. Create a recurrente trip (active by default)
 * 2. Verify status is "Activo"
 * 3. Click "⏸️ Pausar" button
 * 4. Confirm the pause dialog
 * 5. Verify status changes to "Inactivo"
 * 6. Verify "▶️ Reanudar" button appears
 * 7. Click "▶️ Reanudar" button
 * 8. Verify status returns to "Activo"
 * 9. Clean up
 */
import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip, setupDialogHandler } from './trips-helpers';

test.describe('Pause and Resume Recurring Trip', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
  });

  test('should pause an active recurring trip', async ({ page }: { page: Page }) => {
    // Step 1: Create a recurrente trip (active by default)
    const tripId = await createTestTrip(
      page,
      'recurrente',
      '2026-04-10T08:00',
      30,
      8,
      'Pause Test Trip',
      { day: '1', time: '08:00' },
    );

    // Step 2: Find the trip card
    const tripCard = page.locator('.trip-card', { hasText: 'Pause Test Trip' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Verify initial status is "Activo"
    await expect(tripCard.getByText('Activo')).toBeVisible();

    // Step 4: Verify "⏸️ Pausar" button is visible
    await expect(tripCard.getByText('Pausar')).toBeVisible();

    // Step 5: Set up confirm dialog handler and click Pause
    const confirmPromise = setupDialogHandler(page, true);
    await tripCard.getByText('Pausar').click();

    // Step 6: Verify confirm dialog appeared
    const confirmMsg = await confirmPromise;
    expect(confirmMsg).toContain('¿Estás seguro de que quieres pausar este viaje recurrente?');

    // Step 7: Handle the success alert
    const alertPromise = setupDialogHandler(page, true);
    const alertMsg = await alertPromise;
    expect(alertMsg).toContain('Viaje pausado');

    // Step 8: Verify status changed to "Inactivo"
    await expect(tripCard.getByText('Inactivo')).toBeVisible();

    // Step 9: Verify "▶️ Reanudar" button now appears instead of Pausar
    await expect(tripCard.getByText('Reanudar')).toBeVisible();

    // Step 10: Clean up
    await deleteTestTrip(page, '2026-04-10T08:00-Pause Test Trip');
  });

  test('should resume a paused recurring trip', async ({ page }: { page: Page }) => {
    // Step 1: Create a recurrente trip
    const tripId = await createTestTrip(
      page,
      'recurrente',
      '2026-04-11T09:00',
      25,
      7,
      'Resume Test Trip',
      { day: '3', time: '09:00' },
    );

    // Step 2: Find the trip card
    const tripCard = page.locator('.trip-card', { hasText: 'Resume Test Trip' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Pause the trip first
    const pauseConfirmPromise = setupDialogHandler(page, true);
    await tripCard.getByText('Pausar').click();
    await pauseConfirmPromise;

    // Handle pause success alert
    const pauseAlertPromise = setupDialogHandler(page, true);
    await pauseAlertPromise;

    // Step 4: Verify trip is now paused (Inactivo)
    await expect(tripCard.getByText('Inactivo')).toBeVisible();

    // Step 5: Click "▶️ Reanudar" button (resume does not have confirm dialog)
    const resumeAlertPromise = setupDialogHandler(page, true);
    await tripCard.getByText('Reanudar').click();
    const resumeAlertMsg = await resumeAlertPromise;
    expect(resumeAlertMsg).toContain('Viaje reanudado');

    // Step 6: Verify status returns to "Activo"
    await expect(tripCard.getByText('Activo')).toBeVisible();

    // Step 7: Verify "⏸️ Pausar" button appears again
    await expect(tripCard.getByText('Pausar')).toBeVisible();

    // Step 8: Clean up
    await deleteTestTrip(page, '2026-04-11T09:00-Resume Test Trip');
  });
});
