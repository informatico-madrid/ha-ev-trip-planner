import { test, expect } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers';

test.describe('Create Trip', () => {
  test('should create a new trip with valid data', async ({ page }) => {
    await navigateToPanel(page);

    const datetime = '2026-04-15T08:30';
    const km = 50;
    const kwh = 15;
    const description = 'Test Commute';

    const tripId = await createTestTrip(page, 'puntual', datetime, km, kwh, description);

    // Assert trip appears in trips list after creation
    const tripCard = page.locator('.trip-card').filter({ hasText: description });
    await expect(tripCard).toBeVisible();

    // Assert trip values match: km=50, kwh=15, description="Test Commute"
    await expect(tripCard.getByText(/50/)).toBeVisible();
    await expect(tripCard.getByText(/15/)).toBeVisible();
    await expect(tripCard.getByText(description)).toBeVisible();

    // Clean up: delete the created trip after test
    await deleteTestTrip(page, tripId);
  });
});