/**
 * Delete Trip E2E Test
 *
 * Purpose: Verifies the complete deletion flow for a trip:
 * 1. Navigate to the EV Trip Planner panel
 * 2. Create a test trip with known data
 * 3. Verify the trip appears in the list
 * 4. Trigger deletion via the delete button
 * 5. Confirm the deletion in the browser dialog
 * 6. Verify the trip is removed from the list
 *
 * Expected confirm dialog text: "¿Estás seguro de que quieres eliminar este viaje?"
 * Expected success alert: "✅ Viaje eliminado"
 */
import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, navigateToPanel, setupDialogHandler } from './trips-helpers';

test.describe('Delete Trip', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
  });

  test('should delete an existing puntual trip', async ({ page }: { page: Page }) => {
    // Step 1: Create a puntual trip for deletion testing
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-08T10:00',
      20,
      5,
      'Delete Test Trip',
    );

    // Step 2: Verify the trip appears in the UI
    const tripCard = page.locator('.trip-card', { hasText: 'Delete Test Trip' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Set up confirm dialog handler BEFORE clicking delete
    const confirmPromise = setupDialogHandler(page, true);

    // Step 4: Click the delete button (🗑️ Eliminar)
    await tripCard.getByText('Eliminar').click();

    // Step 5: Verify confirm dialog message
    const confirmMsg = await confirmPromise;
    expect(confirmMsg).toContain('¿Estás seguro de que quieres eliminar este viaje?');

    // Step 6: Handle the success alert that follows
    const alertPromise = setupDialogHandler(page, true);
    const alertMsg = await alertPromise;
    expect(alertMsg).toContain('Viaje eliminado');

    // Step 7: Verify the trip is no longer visible
    await expect(page.getByText('Delete Test Trip')).toBeHidden();
  });

  test('should cancel deletion when user dismisses confirm dialog', async ({ page }: { page: Page }) => {
    // Step 1: Create a trip
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-09T11:00',
      15,
      4,
      'Cancel Delete Test',
    );

    // Step 2: Verify the trip exists
    const tripCard = page.locator('.trip-card', { hasText: 'Cancel Delete Test' }).last();
    await expect(tripCard).toBeVisible();

    // Step 3: Set up dialog to DISMISS (cancel deletion)
    const confirmPromise = setupDialogHandler(page, false);

    // Step 4: Click delete button
    await tripCard.getByText('Eliminar').click();

    // Step 5: Verify confirm dialog appeared
    const confirmMsg = await confirmPromise;
    expect(confirmMsg).toContain('¿Estás seguro de que quieres eliminar este viaje?');

    // Step 6: Trip should still be visible (deletion was cancelled)
    await expect(page.getByText('Cancel Delete Test')).toBeVisible();

    // Step 7: Clean up - actually delete the trip now
    const deleteConfirmPromise = setupDialogHandler(page, true);
    await tripCard.getByText('Eliminar').click();
    await deleteConfirmPromise;

    // Handle success alert
    const alertPromise = setupDialogHandler(page, true);
    await alertPromise;
  });
});
