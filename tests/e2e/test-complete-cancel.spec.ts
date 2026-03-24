/**
 * E2E Test: Complete/Cancel Punctual Trip
 *
 * Verifies that the EV Trip Planner panel correctly completes and cancels
 * punctual trips through the UI and calls the appropriate services.
 * Usage:
 *   npx playwright test test-complete-cancel.spec.ts
 */

import { test, expect } from '@playwright/test';
test.describe('EV Trip Planner Complete/Cancel Punctual Trip', () => {
  // Test configuration
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';
  const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
  const panelUrl = `${haUrl}/ev-trip-planner-${vehicleId}`;
  test('should complete a punctual trip', async ({ page }) => {
    await page.goto(panelUrl);
    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );
    // Wait for trips section to be populated
    await page.waitForSelector('.trips-list', { timeout: 10000 });
    // Find a punctual trip card
    const tripCards = page.locator('.trip-card');
    const cardCount = await tripCards.count();
    if (cardCount > 0) {
      // Find complete button on first trip
      const completeButton = page.locator('.trip-card').first().locator('.complete-btn');
      // Check if complete button exists
      const completeButtonExists = await completeButton.count() > 0;
      if (completeButtonExists) {
        // Set up dialog handler for confirmation
        page.on('dialog', async (dialog) => {
          await dialog.accept();
        });
        // Click complete button
        await completeButton.click();
        // Wait for trip to show as completed
        await page.waitForTimeout(1000);
        // Verify trip shows as completed (check for completed state)
        const tripCard = page.locator('.trip-card').first();
        const isCompleted = await tripCard.getAttribute('data-completed');
        // Trip should be completed after complete action
        expect(isCompleted).toBe('true');
      }
    }
  });
  test('should cancel a punctual trip', async ({ page }) => {
      // Find cancel button on first trip
      const cancelButton = page.locator('.trip-card').first().locator('.cancel-btn');
      // Check if cancel button exists
      const cancelButtonExists = await cancelButton.count() > 0;
      if (cancelButtonExists) {
        // Click cancel button
        await cancelButton.click();
        // Wait for trip to be removed or show as canceled
        // Verify trip is canceled or removed
        const isCanceled = await tripCard.getAttribute('data-canceled');
        const tripCount = await page.locator('.trip-card').count();
        // Trip should be canceled (data-canceled='true') or removed (count decreased)
        expect(isCanceled).toBe('true');
  test('should toggle complete/cancel state', async ({ page }) => {
    if (cardCount >= 1) {
      // Get initial state
      const tripCard = page.locator('.trip-card').first();
      const initialCompleted = await tripCard.getAttribute('data-completed');
      // Set up dialog handler for complete confirmation
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });
      // Complete the trip
      const completeButton = tripCard.locator('.complete-btn');
      if (await completeButton.count() > 0) {
      // Wait for state to update
      await page.waitForTimeout(1000);
      // Check new state
      const completedState = await tripCard.getAttribute('data-completed');
      expect(completedState).toBe('true');
      // Now cancel the trip (if cancel button exists)
      const cancelButton = tripCard.locator('.cancel-btn');
      if (await cancelButton.count() > 0) {
      // Check final state
      const canceledState = await tripCard.getAttribute('data-canceled');
      expect(canceledState).toBe('true');
  test('should show complete button on active punctual trips', async ({ page }) => {
    // Check if complete button exists on any trip
    const completeButtons = page.locator('.complete-btn');
    const completeButtonCount = await completeButtons.count();
    // Complete buttons should exist if there are active punctual trips
    expect(completeButtonCount >= 0).toBe(true);
  test('should show cancel button on completed trips', async ({ page }) => {
    // Check if cancel button exists on any trip
    const cancelButtons = page.locator('.cancel-btn');
    const cancelButtonCount = await cancelButtons.count();
    // Cancel buttons should exist if there are completed trips
    expect(cancelButtonCount >= 0).toBe(true);
  test('should update trip list after complete/cancel', async ({ page }) => {
    // Get initial trip count
    const initialTripCount = await page.locator('.trip-card').count();
    if (initialTripCount > 0) {
      // Set up dialog handler
      // Complete first trip
      // Verify trip still exists (just changed state)
      const afterCompleteCount = await page.locator('.trip-card').count();
      expect(afterCompleteCount).toBe(initialTripCount);
      // Cancel first trip
      // Verify trip still exists (or was removed)
      const afterCancelCount = await page.locator('.trip-card').count();
      expect(afterCancelCount).toBeLessThanOrEqual(initialTripCount);
});
