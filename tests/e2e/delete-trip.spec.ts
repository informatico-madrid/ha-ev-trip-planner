import { test, expect, type Page } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip, type TripType, type TripData } from './trips-helpers';

/**
 * Delete Trip E2E Test
 *
 * This test verifies the complete deletion flow for a trip:
 * 1. Navigate to the EV Trip Planner panel
 * 2. Create a test trip with known data
 * 3. Verify the trip appears in the list
 * 4. Trigger deletion via the delete button
 * 5. Confirm the deletion in the browser dialog
 * 6. Verify the trip is removed from the list
 *
 * Expected dialog text: "¿Estás seguro de que quieres eliminar este viaje?"
 * (Spanish: "Are you sure you want to delete this trip?")
 */
test.describe('Delete Trip', () => {
  test('should delete an existing trip', async ({ page }: { page: Page }) => {
    // Navigate to the EV Trip Planner panel in Home Assistant
    await navigateToPanel(page);

    // Create a puntual trip with specific attributes for deletion testing:
    // - Type: puntual (one-time trip)
    // - Date/Time: Wednesday April 8, 2026 at 10:00
    // - Distance: 20 km
    // - Energy: 5 kWh
    // - Name: "Delete Test Trip" (unique identifier for this test)
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-08T10:00', // Wednesday April 8, 2026 at 10:00
      20,
      5,
      'Delete Test Trip',
    );

    // Verify the newly created trip appears in the UI before attempting deletion
    const tripCard = page.locator('div').filter({ hasText: 'Delete Test Trip' }).last();
    await expect(tripCard).toBeVisible();

    // Set up dialog handler BEFORE clicking delete to catch the confirmation dialog
    // The dialog is asynchronous, so we register the handler first to avoid race conditions
    let dialogMessage: string = '';
    page.on('dialog', async (dialog) => {
      dialogMessage = dialog.message();
      // Expected dialog text (Spanish): "¿Estás seguro de que quieres eliminar este viaje?"
      // This confirms the user is being asked to explicitly confirm deletion
      expect(dialogMessage).toContain('¿Estás seguro de que quieres eliminar este viaje?');
      // Accept the dialog to proceed with deletion
      await dialog.accept();
    });

    // Click the delete button (trash icon) on the trip card to trigger deletion
    await tripCard.getByRole('button', { name: /delete/i }).click();

    // Verify the trip card is no longer visible after deletion
    await expect(tripCard).toBeHidden();

    // Additional verification: confirm no elements matching "Delete Test Trip" remain
    // Using toHaveCount(0) ensures the trip was completely removed from the list
    const tripListItems = page.locator('div').filter({ hasText: 'Delete Test Trip' });
    await expect(tripListItems).toHaveCount(0);
  });
});
