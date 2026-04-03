import { test, expect } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers';

test.describe('Delete Trip', () => {
  test('should delete an existing trip', async ({ page }) => {
    // Navigate to EV Trip Planner panel
    await navigateToPanel(page);

    // Create a test trip to delete
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-04-15T08:30',
      50,
      15,
      'Test Trip for Deletion',
    );

    // Assert the trip exists before deletion
    const tripCard = page.locator('div').filter({ hasText: 'Test Trip for Deletion' }).last();
    await expect(tripCard).toBeVisible();

    // Delete the trip
    await deleteTestTrip(page, tripId);

    // Assert the trip is removed from the list
    // The trip card should no longer be visible after deletion
    await expect(tripCard).not.toBeVisible();
  });
});
