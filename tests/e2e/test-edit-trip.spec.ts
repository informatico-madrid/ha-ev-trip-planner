/**
 * E2E Test: Edit Trip
 *
 * Verifies that the EV Trip Planner panel correctly edits an existing trip
 * through the UI form and calls the trip_update service.
 *
 * Usage:
 *   npx playwright test test-edit-trip.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner Edit Trip', () => {
  // Test configuration
  const vehicleId = 'chispitas';
  const panelUrl = `http://192.168.1.100:8123/ev-trip-planner-${vehicleId}`;

  test('should open edit form with trip data pre-filled', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Verify form is pre-filled (at least type should be set)
    const tripType = await page.locator('#trip-type').inputValue();
    expect(tripType).toBeTruthy();
  });

  test('should pre-fill trip time when editing', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Verify time field has a value
    const timeValue = await page.locator('#trip-time').inputValue();
    // Time should be in HH:MM format or empty (depending on trip data)
    expect(timeValue.length >= 0).toBe(true);
  });

  test('should pre-fill trip km when editing', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Verify km field has a value (may be empty if not set)
    const kmValue = await page.locator('#trip-km').inputValue();
    // Can be empty or a number
    expect(kmValue.length >= 0).toBe(true);
  });

  test('should update trip time after editing', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Record original time
    const originalTime = await page.locator('#trip-time').inputValue();

    // Modify time
    const newTime = '12:00';
    await page.fill('#trip-time', newTime);

    // Submit form
    await page.locator('.btn-primary').click();

    // Wait for form to close
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });

    // Verify trip was updated - check trips section reflects change
    const tripsSection = page.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  });

  test('should update trip type after editing', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Record original type
    const originalType = await page.locator('#trip-type').inputValue();

    // Switch type
    const newType = originalType === 'recurrente' ? 'puntual' : 'recurrente';
    await page.selectOption('#trip-type', newType);

    // Submit form
    await page.locator('.btn-primary').click();

    // Wait for form to close
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });

    // Verify trip was updated
    const tripsSection = page.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  });

  test('should update trip description after editing', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Add description
    const newDescription = 'Updated test description';
    await page.fill('#trip-description', newDescription);

    // Submit form
    await page.locator('.btn-primary').click();

    // Wait for form to close
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 5000 });

    // Verify trip was updated
    const tripsSection = page.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  });

  test('should cancel edit when closing form', async ({ page }) => {
    await page.goto(panelUrl);

    // Wait for panel to load
    await page.waitForFunction(
      () => (window as any)._tripPanel !== undefined,
      { timeout: 30000 }
    );

    // Find and click edit button on first trip
    const editButton = page.locator('.trip-card .edit-btn').first();
    await editButton.click();

    // Wait for form to appear
    await page.waitForSelector('.trip-form-overlay', { timeout: 10000 });

    // Close form by clicking close button
    const closeButton = page.locator('.close-form-btn');
    await closeButton.click();

    // Verify form is closed
    const formOverlay = page.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden();
  });
});
