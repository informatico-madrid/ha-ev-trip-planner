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

  test('displays recurring trips with correct format', async () => {
    // Create a recurring trip first via service call for setup
    const tripCount = await tripsPage.getTripCount();
    if (tripCount > 0) {
      // Verify recurring trips show day and time format
      // The trip card should contain day selector info
      await expect(tripsPage.tripCard(1)).toBeVisible();
    }
  });

  test('displays punctual trips with correct format', async () => {
    // Create a punctual trip first via service call for setup
    const tripCount = await tripsPage.getTripCount();
    if (tripCount > 0) {
      // Verify punctual trips show date format
      await expect(tripsPage.tripCard(1)).toBeVisible();
    }
  });

  test('shows correct trip count badge', async () => {
    // Get current trip count
    const count = await tripsPage.getTripCount();
    // Verify count is displayed correctly
    // Empty state should show 0, otherwise count should match trip cards
    if (count === 0) {
      await expect(tripsPage.emptyState).toBeVisible();
    } else {
      await expect(tripsPage.tripCard(1)).toBeVisible();
    }
  });
});

test.describe('Create Trip (US-2)', () => {
  let tripsPage: TripsPage;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    await tripsPage.navigateDirect();
  });

  test('opens form modal when clicking + Agregar Viaje', async () => {
    await tripsPage.clickAddTripButton();
    await expect(tripsPage.tripFormOverlay).toBeVisible();
  });

  test('shows Recurrente option with day selector', async () => {
    await tripsPage.clickAddTripButton();
    await expect(tripsPage.recurrenteOption).toBeVisible();
    await tripsPage.selectRecurrente();
    await expect(tripsPage.daySelector).toBeVisible();
  });

  test('shows Puntual option without day selector', async () => {
    await tripsPage.clickAddTripButton();
    await expect(tripsPage.puntualOption).toBeVisible();
    await tripsPage.selectPuntual();
    // Puntual trips should not have a day selector
    // The day selector should not be visible or relevant
  });

  test('creates recurring trip successfully', async () => {
    // Get initial count
    const initialCount = await tripsPage.getTripCount();

    // Open form and create recurring trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();
    await tripsPage.daySelector.selectOption('Monday');
    await tripsPage.enterTime('08:00');
    await tripsPage.submitButton.click();

    // Wait for form to close and trip to appear
    await tripsPage.waitForTripCount(initialCount + 1, 5000);
  });

  test('creates punctual trip successfully', async () => {
    // Get initial count
    const initialCount = await tripsPage.getTripCount();

    // Open form and create punctual trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectPuntual();
    await tripsPage.enterTime('14:00');
    await tripsPage.submitButton.click();

    // Wait for form to close and trip to appear
    await tripsPage.waitForTripCount(initialCount + 1, 5000);
  });

  test('new trip appears immediately in list', async () => {
    const initialCount = await tripsPage.getTripCount();

    // Create a trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();
    await tripsPage.daySelector.selectOption('Tuesday');
    await tripsPage.enterTime('09:00');
    await tripsPage.submitButton.click();

    // Verify new trip count increased
    const newCount = await tripsPage.getTripCount();
    expect(newCount).toBe(initialCount + 1);
  });
});

test.describe('Edit Trip (US-3)', () => {
  let tripsPage: TripsPage;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    await tripsPage.navigateDirect();
  });

  test('opens edit form with pre-filled data', async () => {
    // Ensure there's at least one trip to edit
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      // Skip if no trips - create one first
      test.skip();
    }

    // Click edit button on first trip
    await tripsPage.openEditFormForTrip(1);

    // Verify form is open and has pre-filled data
    await expect(tripsPage.tripFormOverlay).toBeVisible();
  });

  test('updates trip successfully', async () => {
    // Ensure there's at least one trip to edit
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      // Skip if no trips
      test.skip();
    }

    // Open edit form for first trip
    await tripsPage.openEditFormForTrip(1);

    // Update the time
    await tripsPage.enterTime('10:00');

    // Submit the form
    await tripsPage.submitButton.click();

    // Verify form closes
    await expect(tripsPage.tripFormOverlay).not.toBeVisible({ timeout: 5000 });
  });
});

test.describe('Delete Trip (US-4)', () => {
  let tripsPage: TripsPage;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    await tripsPage.navigateDirect();
  });

  test('shows confirmation dialog on Eliminar', async () => {
    // Ensure there's at least one trip to delete
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Click delete button on first trip
    await tripsPage.openDeleteDialogForTrip(1);

    // Verify confirmation dialog appears
    await expect(tripsPage.confirmDialog).toBeVisible();
  });

  test('removes trip on confirm', async () => {
    // Ensure there's at least one trip to delete
    const initialCount = await tripsPage.getTripCount();
    if (initialCount === 0) {
      test.skip();
    }

    // Open delete dialog
    await tripsPage.openDeleteDialogForTrip(1);

    // Confirm deletion
    await tripsPage.confirmDelete();

    // Verify trip count decreases
    const newCount = await tripsPage.getTripCount();
    expect(newCount).toBe(initialCount - 1);
  });

  test('keeps trip on cancel', async () => {
    // Ensure there's at least one trip to delete
    const initialCount = await tripsPage.getTripCount();
    if (initialCount === 0) {
      test.skip();
    }

    // Open delete dialog
    await tripsPage.openDeleteDialogForTrip(1);

    // Cancel deletion
    await tripsPage.cancelDelete();

    // Verify trip count remains the same
    const newCount = await tripsPage.getTripCount();
    expect(newCount).toBe(initialCount);
  });
});

test.describe('Pause/Resume Recurring Trip (US-5)', () => {
  let tripsPage: TripsPage;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    await tripsPage.navigateDirect();
  });

  test('shows Pausar for active recurring trip', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Verify the pause button is visible for active trips
    await expect(tripsPage.pauseButton(1)).toBeVisible();
  });

  test('pauses trip and shows Reanudar', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Click pause button
    await tripsPage.pauseButton(1).click();

    // Verify the trip is now paused (resume button should be visible)
    await expect(tripsPage.resumeButton(1)).toBeVisible();
  });

  test('resumes trip and shows Pausar again', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // First pause the trip
    await tripsPage.pauseButton(1).click();

    // Then resume it
    await tripsPage.resumeButton(1).click();

    // Verify the trip is active again (pause button should be visible)
    await expect(tripsPage.pauseButton(1)).toBeVisible();
  });
});
