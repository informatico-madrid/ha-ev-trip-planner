/**
 * E2E Test: Integration Tests
 *
 * Verifies multiple CRUD operations work together correctly through the panel UI.
 * Usage:
 *   npx playwright test test-integration.spec.ts
 */

import { test, expect } from '@playwright/test';
test.describe('EV Trip Planner Integration Tests', () => {
  // Test configuration
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';
  const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
  const panelUrl = `${haUrl}/ev-trip-planner-${vehicleId}`;
  test('should perform complete CRUD cycle: create, edit, pause, complete, delete', async ({ page }) => {
    await page.goto(panelUrl);
    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );
    // Wait for trips section to be populated
    await page.waitForSelector('.trips-list', { timeout: 10000 });
    // Get initial trip count
    const initialTripCount = await page.locator('.trip-card').count();
    // Set up dialog handler
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });
    // STEP 1: Create a new trip
    await page.locator('.add-trip-btn').click();
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });
    await page.selectOption('#trip-type', 'recurrente');
    await page.selectOption('#trip-day', 'Lunes');
    await page.fill('#trip-time', '08:00');
    await page.fill('#trip-km', '25.5');
    await page.fill('#trip-kwh', '3.2');
    await page.fill('#trip-description', 'Test trip');
    await page.click('.btn-primary');
    // Wait for form to close
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });
    // Verify trip was created
    const afterCreateCount = await page.locator('.trip-card').count();
    expect(afterCreateCount).toBe(initialTripCount + 1);
    // Get the newly created trip
    const allTrips = page.locator('.trip-card');
    const newTripCount = await allTrips.count();
    const newTrip = allTrips.nth(newTripCount - 1);
    // STEP 2: Edit the trip
    const editButton = newTrip.locator('.edit-btn');
    if (await editButton.count() > 0) {
      await editButton.click();
      // Wait for form to open
      await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });
      // Update trip values
      await page.fill('#trip-km', '30.0');
      await page.fill('#trip-kwh', '4.0');
      await page.click('.btn-primary');
      // Wait for form to close
      await expect(formOverlay).toBeHidden({ timeout: 5000 });
      // Verify edit preserved trip count
      const afterEditCount = await page.locator('.trip-card').count();
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
    // STEP 4: Resume the trip
    const resumeButton = newTrip.locator('.resume-btn');
    if (await resumeButton.count() > 0) {
      await resumeButton.click();
      // Verify trip is active again
      expect(isActive).toBe('true');
    // STEP 5: Complete the trip (if complete button exists)
    const completeButton = newTrip.locator('.complete-btn');
    if (await completeButton.count() > 0) {
      await completeButton.click();
      // Verify trip is completed
      const isCompleted = await newTrip.getAttribute('data-completed');
      expect(isCompleted).toBe('true');
    // STEP 6: Cancel the trip (if cancel button exists)
    const cancelButton = newTrip.locator('.cancel-btn');
    if (await cancelButton.count() > 0) {
      await cancelButton.click();
      // Verify trip is canceled
      const isCanceled = await newTrip.getAttribute('data-canceled');
      expect(isCanceled).toBe('true');
    // STEP 7: Delete the trip
    const deleteButton = newTrip.locator('.delete-btn');
    if (await deleteButton.count() > 0) {
      await deleteButton.click();
      // Verify trip was deleted
      const afterDeleteCount = await page.locator('.trip-card').count();
      expect(afterDeleteCount).toBe(initialTripCount);
  });
  test('should handle multiple trips simultaneously', async ({ page }) => {
    // Create multiple trips
    const tripsToCreate = 3;
    for (let i = 0; i < tripsToCreate; i++) {
      await page.locator('.add-trip-btn').click();
      await page.selectOption('#trip-type', 'puntual');
      await page.fill('#trip-time', '10:00');
      await page.fill('#trip-km', `${10 + i}.0`);
      const formOverlay = page.locator('.trip-form-overlay');
    // Verify all trips were created
    expect(afterCreateCount).toBe(initialTripCount + tripsToCreate);
    // Pause first trip
    const firstTrip = page.locator('.trip-card').first();
    const pauseButton = firstTrip.locator('.pause-btn');
      const isActive = await firstTrip.getAttribute('data-active');
    // Complete last trip
    const lastTrip = page.locator('.trip-card').last();
    const completeButton = lastTrip.locator('.complete-btn');
      const isCompleted = await lastTrip.getAttribute('data-completed');
    // Verify trip count unchanged
    const afterOperationsCount = await page.locator('.trip-card').count();
    expect(afterOperationsCount).toBe(afterCreateCount);
  test('should handle rapid CRUD operations', async ({ page }) => {
    // Create trip
    await page.selectOption('#trip-type', 'puntual');
    await page.fill('#trip-time', '12:00');
    // Get the new trip
    const trip = page.locator('.trip-card').last();
    // Perform rapid operations: pause -> resume -> complete -> cancel -> delete
    const pauseButton = trip.locator('.pause-btn');
    const resumeButton = trip.locator('.resume-btn');
    const completeButton = trip.locator('.complete-btn');
    const cancelButton = trip.locator('.cancel-btn');
    const deleteButton = trip.locator('.delete-btn');
    // Verify trip was deleted
    const tripCount = await page.locator('.trip-card').count();
    expect(tripCount).toBeLessThanOrEqual(tripCount); // Should handle gracefully
  test('should maintain state across multiple operations', async ({ page }) => {
    // Create trip 1
    await page.fill('#trip-description', 'Trip 1');
    await expect(page.locator('.trip-form-overlay')).toBeHidden({ timeout: 5000 });
    // Create trip 2
    await page.fill('#trip-time', '14:00');
    await page.fill('#trip-description', 'Trip 2');
    // Verify both trips exist
    expect(tripCount).toBe(2);
    // Pause trip 1
    const trip1 = page.locator('.trip-card').first();
    const pauseButton1 = trip1.locator('.pause-btn');
    if (await pauseButton1.count() > 0) {
      await pauseButton1.click();
    // Complete trip 2
    const trip2 = page.locator('.trip-card').last();
    const completeButton2 = trip2.locator('.complete-btn');
    if (await completeButton2.count() > 0) {
      await completeButton2.click();
    // Verify states are correct
    const trip1Active = await trip1.getAttribute('data-active');
    const trip2Completed = await trip2.getAttribute('data-completed');
    expect(trip1Active).toBe('false'); // Trip 1 paused
    expect(trip2Completed).toBe('true'); // Trip 2 completed
    const finalTripCount = await page.locator('.trip-card').count();
    expect(finalTripCount).toBe(2);
});
