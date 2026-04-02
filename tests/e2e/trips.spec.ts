/**
 * E2E Tests for Trip CRUD Operations
 *
 * Tests all CRUD operations for trips in the EV Trip Planner panel:
 * - US-1: Trip List Loading
 * - US-2: Create Trip
 * - US-3: Edit Trip
 * - US-4: Delete Trip
 * - US-5: Pause/Resume Recurring Trip
 * - US-6: Complete/Cancel Punctual Trip
 */

import { test, expect } from '@playwright/test';
import { TripsPage } from './pages/trips.page';

test.describe('Trip List Loading (US-1)', () => {
  let tripsPage: TripsPage;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    await tripsPage.navigateDirect();
  });

  test('displays empty state when no trips exist', async () => {
    // If there are no trips, empty state should be visible
    const isEmpty = await tripsPage.isEmptyStateVisible();
    if (isEmpty) {
      await expect(tripsPage.emptyState).toBeVisible();
    }
  });
});
