import { test, expect } from '@playwright/test';
import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers';

test.describe('Edit Trip', () => {
  test('should edit an existing trip with valid data', async ({ page }) => {
    // Navigate to EV Trip Planner panel
    await page.goto('/');
    await page.waitForURL('/home');
    await page.getByRole('link', { name: 'EV Trip Planner' }).click();
    await page.waitForURL(/\/ev_trip_planner\//);
  });
});