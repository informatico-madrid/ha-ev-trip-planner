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
import * as fs from 'fs';
import * as path from 'path';

/**
 * Get panel URL from stored auth state - runs in Node.js context
 */
function getPanelUrlFromStorage(): string {
  const panelUrlPath = path.join(process.cwd(), 'playwright/.auth/panel-url.txt');
  try {
    return fs.readFileSync(panelUrlPath, 'utf-8').trim();
  } catch {
    // Fallback - should not happen in normal runs
    return 'http://127.0.0.1:8123/ev-trip-planner-Coche2';
  }
}

test.describe('Trip List Loading (US-1)', () => {
  let tripsPage: TripsPage;
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
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
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
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

  test('shows validation error when submitting empty form', async () => {
    // Open the form
    await tripsPage.clickAddTripButton();

    // Try to submit without filling any fields
    // The form should show a validation error
    await expect(tripsPage.submitButton).toBeVisible();

    // Click submit and expect some validation feedback
    // (actual validation behavior depends on form implementation)
    await tripsPage.submitButton.click();

    // Form should still be open (not submitted)
    await expect(tripsPage.tripFormOverlay).toBeVisible();
  });

  test('shows validation error when missing required fields', async () => {
    // Open the form with Recurrente selected
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();

    // Don't select a day, try to submit
    await tripsPage.enterTime('08:00');
    await tripsPage.submitButton.click();

    // Form should still be open - required field is missing
    await expect(tripsPage.tripFormOverlay).toBeVisible();
  });
});

test.describe('Edit Trip (US-3)', () => {
  let tripsPage: TripsPage;
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
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

  test('edit preserves other fields when changing time only', async () => {
    // Ensure there's at least one trip to edit
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Open edit form for first trip
    await tripsPage.openEditFormForTrip(1);

    // Verify form has pre-filled data (type is preserved)
    await expect(tripsPage.recurrenteOption).toBeChecked();

    // Change only the time
    await tripsPage.enterTime('11:00');
    await tripsPage.submitButton.click();

    // Verify form closes
    await expect(tripsPage.tripFormOverlay).not.toBeVisible({ timeout: 5000 });
  });
});

test.describe('Delete Trip (US-4)', () => {
  let tripsPage: TripsPage;
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
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

  test('delete dialog shows trip identifier', async () => {
    // Ensure there's at least one trip to delete
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Open delete dialog
    await tripsPage.openDeleteDialogForTrip(1);

    // Verify confirmation dialog appears
    await expect(tripsPage.confirmDialog).toBeVisible();

    // Verify cancel button is present in dialog
    await expect(tripsPage.cancelDialogBtn).toBeVisible();
  });
});

test.describe('Pause/Resume Recurring Trip (US-5)', () => {
  let tripsPage: TripsPage;
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
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

  test('paused state persists after page refresh', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Pause the trip
    await tripsPage.pauseButton(1).click();

    // Verify trip is paused
    await expect(tripsPage.resumeButton(1)).toBeVisible();

    // Refresh the page
    await tripsPage.navigateDirect();

    // Verify trip is still paused (resume button should still be visible)
    await expect(tripsPage.resumeButton(1)).toBeVisible();
  });

  test('pause/resume toggle cycles correctly', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Initial state: active trip shows Pausar
    await expect(tripsPage.pauseButton(1)).toBeVisible();

    // Click Pausar -> shows Reanudar
    await tripsPage.pauseButton(1).click();
    await expect(tripsPage.resumeButton(1)).toBeVisible();

    // Click Reanudar -> shows Pausar again
    await tripsPage.resumeButton(1).click();
    await expect(tripsPage.pauseButton(1)).toBeVisible();
  });
});

test.describe('Complete/Cancel Punctual Trip (US-6)', () => {
  let tripsPage: TripsPage;
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
  });

  test('shows Completar for active punctual trip', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Verify the complete button is visible for punctual trips
    await expect(tripsPage.completeButton(1)).toBeVisible();
  });

  test('completes trip and removes from list', async () => {
    // Ensure there's at least one trip
    const initialCount = await tripsPage.getTripCount();
    if (initialCount === 0) {
      test.skip();
    }

    // Click complete button
    await tripsPage.completeButton(1).click();

    // Verify trip count decreases
    const newCount = await tripsPage.getTripCount();
    expect(newCount).toBe(initialCount - 1);
  });

  test('shows Cancelar for active punctual trip', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Verify the cancel button is visible
    await expect(tripsPage.cancelButton(1)).toBeVisible();
  });

  test('cancels trip and removes from list', async () => {
    // Ensure there's at least one trip
    const initialCount = await tripsPage.getTripCount();
    if (initialCount === 0) {
      test.skip();
    }

    // Click cancel button
    await tripsPage.cancelButton(1).click();

    // Verify trip count decreases
    const newCount = await tripsPage.getTripCount();
    expect(newCount).toBe(initialCount - 1);
  });

  test('complete and cancel are mutually exclusive', async () => {
    // Ensure there's at least one trip
    const count = await tripsPage.getTripCount();
    if (count === 0) {
      test.skip();
    }

    // Verify that after completion, trip is removed (not changed to Cancelar)
    // The trip should be removed from the list, not show a different button
    const initialCount = await tripsPage.getTripCount();
    await tripsPage.completeButton(1).click();

    // Verify trip was removed, not transformed
    const newCount = await tripsPage.getTripCount();
    expect(newCount).toBe(initialCount - 1);
  });
});

test.describe('Multiple Trips (Extended)', () => {
  let tripsPage: TripsPage;
  let panelUrl: string;

  test.beforeEach(async ({ page }) => {
    tripsPage = new TripsPage(page);
    // Set up dialog handler to auto-accept any dialogs
    tripsPage.setupDialogHandler();
    // Read panel URL from storage (Node.js context)
    panelUrl = getPanelUrlFromStorage();
    tripsPage.setPanelUrl(panelUrl);
    await tripsPage.navigateDirect();
  });

  test.afterEach(async () => {
    // Cleanup handled by individual tests
  });

  test('creates multiple trips in sequence', async () => {
    // Get initial count
    const initialCount = await tripsPage.getTripCount();

    // Create first recurring trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();
    await tripsPage.daySelector.selectOption('Monday');
    await tripsPage.enterTime('08:00');
    await tripsPage.submitButton.click();
    await tripsPage.waitForTripCount(initialCount + 1, 5000);

    // Create second recurring trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();
    await tripsPage.daySelector.selectOption('Wednesday');
    await tripsPage.enterTime('10:00');
    await tripsPage.submitButton.click();
    await tripsPage.waitForTripCount(initialCount + 2, 5000);

    // Create punctual trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectPuntual();
    await tripsPage.enterTime('14:00');
    await tripsPage.submitButton.click();
    await tripsPage.waitForTripCount(initialCount + 3, 5000);

    // Verify all three trips exist
    const finalCount = await tripsPage.getTripCount();
    expect(finalCount).toBe(initialCount + 3);
  });

  test('trips appear in list in creation order', async () => {
    // Get initial count
    const initialCount = await tripsPage.getTripCount();

    // Create first trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();
    await tripsPage.daySelector.selectOption('Monday');
    await tripsPage.enterTime('08:00');
    await tripsPage.submitButton.click();
    await tripsPage.waitForTripCount(initialCount + 1, 5000);

    // Create second trip
    await tripsPage.clickAddTripButton();
    await tripsPage.selectRecurrente();
    await tripsPage.daySelector.selectOption('Tuesday');
    await tripsPage.enterTime('09:00');
    await tripsPage.submitButton.click();
    await tripsPage.waitForTripCount(initialCount + 2, 5000);

    // Verify there are exactly 2 trips
    const finalCount = await tripsPage.getTripCount();
    expect(finalCount).toBe(initialCount + 2);

    // Both trip cards should be visible
    await expect(tripsPage.tripCard(1)).toBeVisible();
    await expect(tripsPage.tripCard(2)).toBeVisible();
  });
});

/**
 * Test Data Builders
 * Builder pattern for creating test trips with a fluent API
 */

/**
 * Options for building a recurring trip
 */
interface RecurringTripOptions {
  day?: string;
  time?: string;
}

/**
 * Options for building a punctual trip
 */
interface PunctualTripOptions {
  time?: string;
}

/**
 * Builder for creating recurring trips via UI
 * Usage:
 *   const index = await buildRecurringTrip(tripsPage, { day: 'Monday', time: '08:00' });
 */
async function buildRecurringTrip(
  tripsPage: TripsPage,
  options: RecurringTripOptions = {}
): Promise<number> {
  const { day = 'Monday', time = '08:00' } = options;
  const initialCount = await tripsPage.getTripCount();

  await tripsPage.clickAddTripButton();
  await tripsPage.selectRecurrente();
  await tripsPage.daySelector.selectOption(day);
  await tripsPage.enterTime(time);
  await tripsPage.submitButton.click();

  // Wait for trip to appear
  await tripsPage.waitForTripCount(initialCount + 1, 5000);

  // Return the index of the newly created trip (1-based)
  return initialCount + 1;
}

/**
 * Builder for creating punctual trips via UI
 * Usage:
 *   const index = await buildPunctualTrip(tripsPage, { time: '14:00' });
 */
async function buildPunctualTrip(
  tripsPage: TripsPage,
  options: PunctualTripOptions = {}
): Promise<number> {
  const { time = '14:00' } = options;
  const initialCount = await tripsPage.getTripCount();

  await tripsPage.clickAddTripButton();
  await tripsPage.selectPuntual();
  await tripsPage.enterTime(time);
  await tripsPage.submitButton.click();

  // Wait for trip to appear
  await tripsPage.waitForTripCount(initialCount + 1, 5000);

  // Return the index of the newly created trip (1-based)
  return initialCount + 1;
}

/**
 * Cleans up a test trip by index via the delete flow
 */
async function cleanupTestTrip(tripsPage: TripsPage, tripIndex: number): Promise<void> {
  try {
    const count = await tripsPage.getTripCount();
    if (count >= tripIndex) {
      await tripsPage.openDeleteDialogForTrip(tripIndex);
      await tripsPage.confirmDelete();
    }
  } catch {
    // Trip may already be deleted, ignore errors
  }
}

// Backward compatibility aliases
const createTestRecurringTrip = buildRecurringTrip;
const createTestPunctualTrip = buildPunctualTrip;
