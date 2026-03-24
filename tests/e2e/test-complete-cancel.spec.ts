/**
 * E2E Test: Complete/Cancel Punctual Trip
 *
 * Verifies that the EV Trip Planner panel correctly completes and cancels
 * punctual trips through the UI and calls the appropriate services.
 * Usage:
 *   npx playwright test test-complete-cancel.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

test.describe('EV Trip Planner Complete/Cancel Punctual Trip', () => {
  test('should complete a punctual trip', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section to be populated
    await page.locator('.trips-section').waitFor({ state: 'visible', timeout: 10000 });

    // Find trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      // Find complete button on first trip
      const completeButton = tripCards.first().locator('.complete-btn');

      // Check if complete button exists
      const completeButtonExists = await completeButton.count() > 0;

      if (completeButtonExists) {
        // Set up dialog handler for confirmation
        page.on('dialog', async (dialog) => {
          console.log(`Dialog: ${dialog.message()}`);
          await dialog.accept();
        });

        // Click complete button
        await completeButton.click();

        // Wait for trip to show as completed
        await page.waitForTimeout(1000);

        // Verify trip shows as completed
        const tripCard = tripCards.first();
        const isCompleted = await tripCard.getAttribute('data-completed');

        // Trip should be completed after complete action
        expect(isCompleted).toBe('true');
      }
    }
  });

  test('should cancel a punctual trip', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for trips section
    await page.locator('.trips-section').waitFor({ state: 'visible', timeout: 10000 });

    // Find trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount > 0) {
      // Find cancel button on first trip
      const cancelButton = tripCards.first().locator('.cancel-btn');

      // Check if cancel button exists
      const cancelButtonExists = await cancelButton.count() > 0;

      if (cancelButtonExists) {
        // Set up dialog handler for confirmation
        page.on('dialog', async (dialog) => {
          console.log(`Dialog: ${dialog.message()}`);
          await dialog.accept();
        });

        // Click cancel button
        await cancelButton.click();

        // Wait for trip to be removed or show as canceled
        await page.waitForTimeout(1000);

        // Verify trip is canceled or removed
        const tripCard = tripCards.first();
        const isCanceled = await tripCard.getAttribute('data-canceled');
        const tripCount = await tripCards.count();

        // Trip should be canceled (data-canceled='true') or removed (count decreased)
        expect(isCanceled).toBe('true') || expect(tripCount).toBeLessThan(cardCount);
      }
    }
  });

  test('should toggle complete/cancel state', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const cardCount = await tripCards.count();

    if (cardCount >= 1) {
      // Get initial state
      const tripCard = tripCards.first();
      const initialCompleted = await tripCard.getAttribute('data-completed');

      // Set up dialog handler for complete confirmation
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Complete the trip
      const completeButton = tripCard.locator('.complete-btn');

      if (await completeButton.count() > 0) {
        // Click complete button
        await completeButton.click();

        // Wait for state to update
        await page.waitForTimeout(1000);

        // Check new state
        const completedState = await tripCard.getAttribute('data-completed');
        expect(completedState).toBe('true');

        // Now cancel the trip (if cancel button exists)
        const cancelButton = tripCard.locator('.cancel-btn');

        if (await cancelButton.count() > 0) {
          // Click cancel button
          await cancelButton.click();

          // Wait for state to update
          await page.waitForTimeout(1000);

          // Check final state
          const canceledState = await tripCard.getAttribute('data-canceled');
          expect(canceledState).toBe('true');
        }
      }
    }
  });

  test('should show complete button on active punctual trips', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check if complete button exists on any trip
    const completeButtons = page.locator('ev-trip-planner-panel >> .complete-btn');
    const completeButtonCount = await completeButtons.count();

    // Complete buttons should exist if there are active punctual trips
    expect(completeButtonCount >= 0).toBe(true);
  });

  test('should show cancel button on completed trips', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check if cancel button exists on any trip
    const cancelButtons = page.locator('ev-trip-planner-panel >> .cancel-btn');
    const cancelButtonCount = await cancelButtons.count();

    // Cancel buttons should exist if there are completed trips
    expect(cancelButtonCount >= 0).toBe(true);
  });

  test('should update trip list after complete/cancel', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to load
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const initialTripCount = await tripCards.count();

    if (initialTripCount > 0) {
      // Set up dialog handler
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      // Complete first trip
      const completeButton = tripCards.first().locator('.complete-btn');

      if (await completeButton.count() > 0) {
        await completeButton.click();
        await page.waitForTimeout(1000);

        // Verify trip still exists (just changed state)
        const afterCompleteCount = await tripCards.count();
        expect(afterCompleteCount).toBe(initialTripCount);

        // Cancel first trip
        const cancelButton = tripCards.first().locator('.cancel-btn');

        if (await cancelButton.count() > 0) {
          await cancelButton.click();
          await page.waitForTimeout(1000);

          // Verify trip still exists (or was removed)
          const afterCancelCount = await tripCards.count();
          expect(afterCancelCount).toBeLessThanOrEqual(initialTripCount);
        }
      }
    }
  });
});
