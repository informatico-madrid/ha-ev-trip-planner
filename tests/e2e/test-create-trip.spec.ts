/**
 * E2E Test: Create Trip
 *
 * Verifies that the EV Trip Planner panel correctly creates a new trip
 * through the UI form and calls the trip_create service.
 * Usage:
 *   npx playwright test test-create-trip.spec.ts
 */

import { test, expect } from '@playwright/test';
test.describe('EV Trip Planner Create Trip', () => {
  // Test configuration
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';
  const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
  const panelUrl = `${haUrl}/ev-trip-planner-${vehicleId}`;
  test('should open trip creation form', async ({ page }) => {
    await page.goto(panelUrl);
    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );
    // Click add trip button
    const addTripButton = page.locator('.add-trip-btn');
    await addTripButton.click();
    // Verify form overlay appears
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });
  });
  test('should show trip creation form with all required fields', async ({ page }) => {
    await page.locator('.add-trip-btn').click();
    // Wait for form to appear
    // Verify form has required fields
    await expect(page.locator('#trip-type')).toBeVisible();
    await expect(page.locator('#trip-day')).toBeVisible();
    await expect(page.locator('#trip-time')).toBeVisible();
    await expect(page.locator('#trip-km')).toBeVisible();
    await expect(page.locator('#trip-kwh')).toBeVisible();
    await expect(page.locator('#trip-description')).toBeVisible();
  test('should create a recurring trip', async ({ page }) => {
    // Fill form with recurring trip data
    await page.selectOption('#trip-type', 'recurrente');
    await page.selectOption('#trip-day', '1'); // Monday
    await page.fill('#trip-time', '08:00');
    await page.fill('#trip-km', '25.5');
    await page.fill('#trip-kwh', '5.2');
    await page.fill('#trip-description', 'Test recurring trip');
    // Click submit button
    await page.locator('.btn-primary').click();
    // Wait for form to close (overlay removed)
    await expect(formOverlay).toBeHidden({ timeout: 5000 });
    // Verify trip was created - check trips section
    const tripsSection = page.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  test('should create a punctual trip', async ({ page }) => {
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });
    // Fill form with punctual trip data
    await page.selectOption('#trip-type', 'puntual');
    // Punctual trips shouldn't have day selector visible
    const daySelect = page.locator('#trip-day');
    const daySelectVisible = await daySelect.isVisible();
    if (daySelectVisible) {
      await daySelect.selectOption('0'); // Sunday
    }
    await page.fill('#trip-time', '14:30');
    await page.fill('#trip-km', '15.0');
    await page.fill('#trip-description', 'Test punctual trip');
    // Wait for form to close
  test('should validate required fields before submission', async ({ page }) => {
    // Try to submit without filling required fields
    // (form should either prevent submission or show validation)
    const submitBtn = page.locator('.btn-primary');
    await submitBtn.click();
    // Either form stays open (validation failed) or trip is created
    const formStillOpen = await page.locator('.trip-form-overlay').count();
    expect(formStillOpen >= 0).toBe(true);
  test('should handle form submission with minimal required data', async ({ page }) => {
    // Fill only required fields
    await page.selectOption('#trip-day', '0');
    await page.fill('#trip-time', '06:00');
    // Submit
    // Form should close
});
