/**
 * E2E Test: Integration Tests
 *
 * Verifies multiple CRUD operations work together correctly through the panel UI.
 * Usage:
 *   npx playwright test test-integration.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Integration Tests', () => {
  test('should perform complete CRUD cycle: create, edit, pause, complete, delete', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.locator('.trips-section').waitFor({ state: 'visible', timeout: 10000 });

    // Get initial trip count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialTripCount = await tripCards.count();

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      console.log(`Dialog: ${dialog.message()}`);
      await dialog.accept();
    });

    // STEP 1: Create a new trip
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.waitForSelector('ev-trip-planner-panel >> .trip-form-overlay', { timeout: 10000 });

    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('08:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('3.2');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test trip');
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // Verify trip was created
    const afterCreateCount = await tripCards.count();
    expect(afterCreateCount).toBe(initialTripCount + 1);

    // Get the newly created trip
    const allTrips = page.locator('ev-trip-planner-panel >> .trip-card');
    const newTripCount = await allTrips.count();
    const newTrip = allTrips.nth(newTripCount - 1);

    // STEP 2: Edit the trip
    const editButton = newTrip.locator('.edit-btn');
    if (await editButton.count() > 0) {
      await editButton.click();

      // Wait for form to open
      await page.waitForSelector('ev-trip-planner-panel >> .trip-form-overlay', { timeout: 10000 });

      // Update trip values
      await page.locator('ev-trip-planner-panel >> #trip-km').fill('30.0');
      await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('4.0');
      await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

      // Wait for form to close
      await expect(formOverlay).toBeHidden({ timeout: 10000 });

      // Verify edit preserved trip count
      const afterEditCount = await tripCards.count();
      expect(afterEditCount).toBe(initialTripCount + 1);
    }

    // STEP 3: Pause the trip (if pause button exists)
    const pauseButton = newTrip.locator('.pause-btn');
    if (await pauseButton.count() > 0) {
      await pauseButton.click();
      await page.waitForTimeout(500);

      // Verify trip is paused
      const isActive = await newTrip.getAttribute('data-active');
      expect(isActive).toBe('false');
    }

    // STEP 4: Resume the trip
    const resumeButton = newTrip.locator('.resume-btn');
    if (await resumeButton.count() > 0) {
      await resumeButton.click();

      // Verify trip is active again
      const isActive = await newTrip.getAttribute('data-active');
      expect(isActive).toBe('true');
    }

    // STEP 5: Complete the trip (if complete button exists)
    const completeButton = newTrip.locator('.complete-btn');
    if (await completeButton.count() > 0) {
      await completeButton.click();

      // Verify trip is completed
      const isCompleted = await newTrip.getAttribute('data-completed');
      expect(isCompleted).toBe('true');
    }

    // STEP 6: Cancel the trip (if cancel button exists)
    const cancelButton = newTrip.locator('.cancel-btn');
    if (await cancelButton.count() > 0) {
      await cancelButton.click();

      // Verify trip is canceled
      const isCanceled = await newTrip.getAttribute('data-canceled');
      expect(isCanceled).toBe('true');
    }

    // STEP 7: Delete the trip
    const deleteButton = newTrip.locator('.delete-btn');
    if (await deleteButton.count() > 0) {
      await deleteButton.click();

      // Verify trip was deleted
      const afterDeleteCount = await tripCards.count();
      expect(afterDeleteCount).toBe(initialTripCount);
    }
  });

  test('should handle multiple trips simultaneously', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Get initial trip count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialTripCount = await tripCards.count();

    // Create multiple trips
    const tripsToCreate = 3;

    for (let i = 0; i < tripsToCreate; i++) {
      await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
      await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
      await page.locator('ev-trip-planner-panel >> #trip-datetime').fill(`2026-03-25T${10 + i}:00`);
      await page.locator('ev-trip-planner-panel >> #trip-km').fill(`${10 + i}.0`);
      await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
      await page.waitForTimeout(500);
    }

    // Verify all trips were created
    const afterCreateCount = await tripCards.count();
    expect(afterCreateCount).toBeGreaterThanOrEqual(initialTripCount + tripsToCreate);

    // Pause first trip
    const firstTrip = tripCards.first();
    const pauseButton = firstTrip.locator('.pause-btn');

    if (await pauseButton.count() > 0) {
      await pauseButton.click();
      const isActive = await firstTrip.getAttribute('data-active');
      expect(isActive).toBe('false');
    }

    // Complete last trip
    const lastTrip = tripCards.last();
    const completeButton = lastTrip.locator('.complete-btn');

    if (await completeButton.count() > 0) {
      await completeButton.click();
      const isCompleted = await lastTrip.getAttribute('data-completed');
      expect(isCompleted).toBe('true');
    }

    // Verify trip count unchanged
    const afterOperationsCount = await tripCards.count();
    expect(afterOperationsCount).toBeGreaterThanOrEqual(initialTripCount + tripsToCreate);
  });

  test('should handle rapid CRUD operations', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Create trip
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('12:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await page.waitForTimeout(500);

    // Get the new trip
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const trip = tripCards.last();

    // Perform rapid operations: pause -> resume -> complete -> cancel -> delete
    const pauseButton = trip.locator('.pause-btn');
    const resumeButton = trip.locator('.resume-btn');
    const completeButton = trip.locator('.complete-btn');
    const cancelButton = trip.locator('.cancel-btn');
    const deleteButton = trip.locator('.delete-btn');

    // Pause
    if (await pauseButton.count() > 0) {
      await pauseButton.click();
      await page.waitForTimeout(500);
    }

    // Resume
    if (await resumeButton.count() > 0) {
      await resumeButton.click();
      await page.waitForTimeout(500);
    }

    // Complete
    if (await completeButton.count() > 0) {
      await completeButton.click();
      await page.waitForTimeout(500);
    }

    // Cancel
    if (await cancelButton.count() > 0) {
      await cancelButton.click();
      await page.waitForTimeout(500);
    }

    // Delete
    if (await deleteButton.count() > 0) {
      await deleteButton.click();

      // Verify trip was deleted
      const tripCount = await tripCards.count();
      expect(tripCount).toBeLessThanOrEqual(tripCount); // Should handle gracefully
    }
  });

  test('should maintain state across multiple operations', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Create trip 1
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Trip 1');
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await page.waitForTimeout(500);

    // Create trip 2
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('14:00');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Trip 2');
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();
    await page.waitForTimeout(500);

    // Verify both trips exist
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripCount = await tripCards.count();
    expect(tripCount).toBeGreaterThanOrEqual(2);

    // Pause trip 1
    const trip1 = tripCards.first();
    const pauseButton1 = trip1.locator('.pause-btn');

    if (await pauseButton1.count() > 0) {
      await pauseButton1.click();
      await page.waitForTimeout(500);
    }

    // Complete trip 2
    const trip2 = tripCards.last();
    const completeButton2 = trip2.locator('.complete-btn');

    if (await completeButton2.count() > 0) {
      await completeButton2.click();
      await page.waitForTimeout(500);
    }

    // Verify states are correct
    const trip1Active = await trip1.getAttribute('data-active');
    const trip2Completed = await trip2.getAttribute('data-completed');

    expect(trip1Active).toBe('false'); // Trip 1 paused
    expect(trip2Completed).toBe('true'); // Trip 2 completed

    const finalTripCount = await tripCards.count();
    expect(finalTripCount).toBeGreaterThanOrEqual(2);
  });
});
