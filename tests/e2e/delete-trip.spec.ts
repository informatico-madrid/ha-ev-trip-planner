import { test, expect } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers';

test.describe('Delete Trip', () => {
  test('should delete an existing trip', async ({ page }) => {
    // T029: Navigate to EV Trip Planner panel
    await navigateToPanel(page);

    // T029: Create a puntual trip (day: Wednesday, time: 10:00, km: 20, kwh: 5)
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-08T10:00', // Wednesday April 8, 2026 at 10:00
      20,
      5,
      'Delete Test Trip',
    );

    // Assert the trip exists before deletion
    const tripCard = page.locator('div').filter({ hasText: 'Delete Test Trip' }).last();
    await expect(tripCard).toBeVisible();

    // T030: Implement delete flow with dialog
    // Step 1: Set up dialog handler before clicking delete
    let dialogMessage = '';
    page.on('dialog', async (dialog) => {
      dialogMessage = dialog.message();
      // Step 2: Assert dialog message contains confirmation text
      expect(dialogMessage).toContain('¿Estás seguro de que quieres eliminar este viaje?');
      // Step 3: Accept dialog
      await dialog.accept();
    });

    // Step 4: Click delete button (trash icon)
    await tripCard.getByRole('button', { name: /delete/i }).click();

    // T031: Assert trip no longer appears in trips list after deletion
    await expect(tripCard).toBeHidden();

    // T031: Use toHaveCount(0) for list verification
    const tripListItems = page.locator('div').filter({ hasText: 'Delete Test Trip' });
    await expect(tripListItems).toHaveCount(0);
  });
});
