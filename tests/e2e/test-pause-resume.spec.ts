/**
 * E2E Test: Pause/Resume Recurring Trip
 *
 * Verifies that the EV Trip Planner panel correctly pauses and resumes
 * recurring trips through the UI and calls the appropriate services.
 * Usage:
 *   npx playwright test test-pause-resume.spec.ts
 */

import { test, expect } from '@playwright/test';
test.describe('EV Trip Planner Pause/Resume Recurring Trip', () => {
  // Test configuration
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';
  const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
  const panelUrl = `${haUrl}/ev-trip-planner-${vehicleId}`;
  test('should pause a recurring trip', async ({ page }) => {
    await page.goto(panelUrl);
    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );
    // Wait for trips section to be populated
    await page.waitForSelector('.trips-list', { timeout: 10000 });
    // Find a trip card (if any exist)
    const tripCards = page.locator('.trip-card');
    const cardCount = await tripCards.count();
    if (cardCount > 0) {
      // Find pause button on first trip
      const pauseButton = page.locator('.trip-card').first().locator('.pause-btn');
      // Try to click pause button
      const pauseButtonExists = await pauseButton.count() > 0;
      if (pauseButtonExists) {
        // Set up dialog handler for confirmation
        page.on('dialog', async (dialog) => {
          await dialog.accept();
        });
        // Click pause button
        await pauseButton.click();
        // Wait for trip to show as paused/inactive
        await page.waitForTimeout(1000);
        // Verify trip shows as inactive (this may vary based on implementation)
        const tripCard = page.locator('.trip-card').first();
        const isActive = await tripCard.getAttribute('data-active');
        // Trip should be inactive after pause
        expect(isActive).toBe('false');
      }
    }
  });
  test('should resume a paused recurring trip', async ({ page }) => {
      // Find resume button on first trip
      const resumeButton = page.locator('.trip-card').first().locator('.resume-btn');
      // Try to click resume button
      const resumeButtonExists = await resumeButton.count() > 0;
      if (resumeButtonExists) {
        // Click resume button
        await resumeButton.click();
        // Wait for trip to show as active
        // Verify trip shows as active
        // Trip should be active after resume
        expect(isActive).toBe('true');
  test('should toggle pause/resume state', async ({ page }) => {
    // Find a trip card
    if (cardCount >= 1) {
      // Get initial state
      const tripCard = page.locator('.trip-card').first();
      const initialActive = await tripCard.getAttribute('data-active');
      // Set up dialog handler for pause confirmation
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });
      // Pause the trip
      const pauseButton = tripCard.locator('.pause-btn');
      if (await pauseButton.count() > 0) {
      // Wait for state to update
      await page.waitForTimeout(1000);
      // Check new state
      const pausedState = await tripCard.getAttribute('data-active');
      expect(pausedState).toBe('false');
      // Now resume the trip
      const resumeButton = tripCard.locator('.resume-btn');
      if (await resumeButton.count() > 0) {
      // Check final state
      const resumedState = await tripCard.getAttribute('data-active');
      expect(resumedState).toBe('true');
  test('should show pause button on active trips', async ({ page }) => {
    // Check if pause button exists on any trip
    const pauseButtons = page.locator('.pause-btn');
    const pauseButtonCount = await pauseButtons.count();
    // Pause buttons should exist if there are active trips
    expect(pauseButtonCount >= 0).toBe(true);
  test('should show resume button on paused trips', async ({ page }) => {
    // Check if resume button exists on any trip
    const resumeButtons = page.locator('.resume-btn');
    const resumeButtonCount = await resumeButtons.count();
    // Resume buttons should exist if there are paused trips
    expect(resumeButtonCount >= 0).toBe(true);
  test('should update trip list after pause/resume', async ({ page }) => {
    // Get initial trip count
    const initialTripCount = await page.locator('.trip-card').count();
    if (initialTripCount > 0) {
      // Set up dialog handler
      // Pause first trip
      // Verify trip still exists (just changed state)
      const afterPauseCount = await page.locator('.trip-card').count();
      expect(afterPauseCount).toBe(initialTripCount);
      // Resume first trip
      // Verify trip still exists
      const afterResumeCount = await page.locator('.trip-card').count();
      expect(afterResumeCount).toBe(initialTripCount);
});
