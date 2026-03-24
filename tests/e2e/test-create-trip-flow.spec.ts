/**
 * E2E Test: Real interactive flow for creating a trip
 *
 * This test validates the complete trip creation flow through real browser
 * interactions, simulating a real user creating a trip via the panel UI.
 *
 * Usage:
 *   npx playwright test test-create-trip-flow.spec.ts
 */

import { test, expect } from '@playwright/test';
import { TripPanel } from './test-base.spec';

test.describe('Create Trip Flow - REAL E2E TEST', () => {

  /**
   * REAL USER FLOW TEST: Create a recurring trip
   *
   * This test simulates a real user:
   * 1. Navigates to the EV Trip Planner panel
   * 2. Clicks "Agregar Viaje" button
   * 3. Fills out the trip form
   * 4. Submits the form
   * 5. Validates the trip appears in the list
   */
  test('should create a recurring trip through real user interaction', async ({ page }) => {
    // Setup: Login and navigate to panel using helper
    const tripPanel = new TripPanel(page, 'Coche2');
    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // STEP 1: Click the "Agregar Viaje" button
    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripBtn).toBeVisible({ timeout: 10000 });
    await addTripBtn.click();

    // STEP 2: Wait for the form overlay to appear
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // STEP 3: Fill out the trip form fields
    // Select trip type: Recurrente
    const tripTypeSelect = page.locator('ev-trip-planner-panel >> #trip-type');
    await tripTypeSelect.selectOption('recurrente');

    // Select day: Lunes (1)
    const tripDaySelect = page.locator('ev-trip-planner-panel >> #trip-day');
    await tripDaySelect.selectOption('1');

    // Fill in the time: 08:00
    const timeInput = page.locator('ev-trip-planner-panel >> #trip-time');
    await timeInput.fill('08:00');

    // Fill in distance: 25.5 km
    const kmInput = page.locator('ev-trip-planner-panel >> #trip-km');
    await kmInput.fill('25.5');

    // Fill in energy: 5.2 kWh
    const kwhInput = page.locator('ev-trip-planner-panel >> #trip-kwh');
    await kwhInput.fill('5.2');

    // Fill in description: "Viaje al trabajo"
    const descriptionTextarea = page.locator('ev-trip-planner-panel >> #trip-description');
    await descriptionTextarea.fill('Viaje al trabajo');

    // STEP 4: Click the submit button
    const submitBtn = page.locator('ev-trip-planner-panel >> button[type="submit"]');
    await submitBtn.click();

    // STEP 5: Wait for form submission and UI update
    await page.waitForTimeout(3000);

    // STEP 6: VALIDATE - The form should be closed (overlay removed)
    const formStillVisible = await formOverlay.count();
    expect(formStillVisible).toBe(0);

    // STEP 7: VALIDATE - Check that trips list section exists
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // STEP 8: VALIDATE - Check for trips-list element
    const tripsList = page.locator('ev-trip-planner-panel >> .trips-list');
    await expect(tripsList).toBeVisible({ timeout: 10000 });

    // STEP 9: VALIDATE - Check that trip cards appear in the list
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount({ min: 1, timeout: 10000 });

    // STEP 10: VALIDATE - Verify trip card contains expected content
    const firstTripCard = tripCards.first();
    await expect(firstTripCard).toBeVisible();

    // Extract and verify trip card content
    const tripCardText = await firstTripCard.textContent();
    expect(tripCardText).toContain('Recurrente');
    expect(tripCardText).toContain('25.5 km');
    expect(tripCardText).toContain('Lunes');
    expect(tripCardText).toContain('08:00');
  });

  /**
   * REAL USER FLOW TEST: Create a punctual trip
   */
  test('should create a punctual trip through real user interaction', async ({ page }) => {
    // Setup: Login and navigate to panel using helper
    const tripPanel = new TripPanel(page, 'Coche2');
    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // STEP 1: Click the "Agregar Viaje" button
    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripBtn).toBeVisible({ timeout: 10000 });
    await addTripBtn.click();

    // STEP 2: Wait for the form to appear
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // STEP 3: Fill out the trip form for a punctual trip
    const tripTypeSelect = page.locator('ev-trip-planner-panel >> #trip-type');
    await tripTypeSelect.selectOption('puntual');

    const datetimeInput = page.locator('ev-trip-planner-panel >> #trip-datetime');
    await datetimeInput.fill('2026-03-25T10:00');

    const kmInput = page.locator('ev-trip-planner-panel >> #trip-km');
    await kmInput.fill('50.0');

    const kwhInput = page.locator('ev-trip-planner-panel >> #trip-kwh');
    await kwhInput.fill('10.5');

    const descriptionTextarea = page.locator('ev-trip-planner-panel >> #trip-description');
    await descriptionTextarea.fill('Viaje a la playa');

    // STEP 4: Click the submit button
    const submitBtn = page.locator('ev-trip-planner-panel >> button[type="submit"]');
    await submitBtn.click();

    // STEP 5: Wait for processing
    await page.waitForTimeout(3000);

    // STEP 6: VALIDATE - Form should be closed
    const formStillVisible = await formOverlay.count();
    expect(formStillVisible).toBe(0);

    // STEP 7: VALIDATE - Check trips list exists
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // STEP 8: VALIDATE - Check for trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount({ min: 1, timeout: 10000 });

    // STEP 9: VALIDATE - Verify trip card content
    const firstTripCard = tripCards.first();
    const tripCardText = await firstTripCard.textContent();
    expect(tripCardText).toContain('Puntual');
    expect(tripCardText).toContain('50.0 km');
  });

  /**
   * REAL USER FLOW TEST: Edit trip
   */
  test('should edit an existing trip', async ({ page }) => {
    // Setup: Login and navigate to panel using helper
    const tripPanel = new TripPanel(page, 'Coche2');
    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // Check if there are existing trips
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    const tripCount = await tripCards.count();

    if (tripCount > 0) {
      // STEP 1: Click edit button on first trip
      const editBtn = page.locator('ev-trip-planner-panel >> .trip-action-btn.edit-btn').first();
      await expect(editBtn).toBeVisible({ timeout: 10000 });
      await editBtn.click();

      // STEP 2: Wait for edit form to appear
      const editFormOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
      await expect(editFormOverlay).toBeVisible({ timeout: 10000 });

      // STEP 3: Modify the trip time
      const editTimeInput = page.locator('ev-trip-planner-panel >> #edit-trip-time');
      await editTimeInput.fill('14:30');

      // STEP 4: Modify the distance
      const editKmInput = page.locator('ev-trip-planner-panel >> #edit-trip-km');
      await editKmInput.fill('40.0');

      // STEP 5: Submit the edit
      const saveBtn = page.locator('ev-trip-planner-panel >> button[type="submit"]');
      await saveBtn.click();

      // STEP 6: Wait for processing
      await page.waitForTimeout(3000);

      // STEP 7: VALIDATE - Form should be closed
      const formStillVisible = await editFormOverlay.count();
      expect(formStillVisible).toBe(0);

      // STEP 8: VALIDATE - Check trips list is updated
      const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
      await expect(tripsSection).toBeVisible({ timeout: 10000 });

      // STEP 9: VALIDATE - Verify trip card contains updated content
      const tripCardsAfterEdit = page.locator('ev-trip-planner-panel >> .trip-card');
      await expect(tripCardsAfterEdit).toHaveCount({ min: 1, timeout: 10000 });

      const tripCardText = await tripCards.first().textContent();
      expect(tripCardText).toContain('40.0 km');
      expect(tripCardText).toContain('14:30');
    } else {
      test.skip('No existing trips to edit');
    }
  });

  /**
   * REAL USER FLOW TEST: Cancel trip creation
   */
  test('should cancel trip creation and close form', async ({ page }) => {
    // Setup: Login and navigate to panel using helper
    const tripPanel = new TripPanel(page, 'Coche2');
    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // STEP 1: Click the "Agregar Viaje" button
    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await addTripBtn.click();

    // STEP 2: Wait for the form to appear
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // STEP 3: Fill some fields
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('30.0');

    // STEP 4: Click the cancel button
    const cancelBtn = page.locator('ev-trip-planner-panel >> .btn-secondary');
    await cancelBtn.click();

    // STEP 5: Verify the form was closed
    await page.waitForTimeout(1000);
    const formClosed = await formOverlay.count();
    expect(formClosed).toBe(0);
  });

  /**
   * REAL USER FLOW TEST: Complete end-to-end trip creation
   */
  test('should complete full trip creation workflow', async ({ page }) => {
    // Setup: Login and navigate to panel using helper
    const tripPanel = new TripPanel(page, 'Coche2');
    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // Step 1: Verify initial state - trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // Step 2: Click add trip button
    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await addTripBtn.click();

    // Step 3: Form appears - verify form overlay is visible
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Step 4: Fill all form fields
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('3');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('09:30');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('35.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('7.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Prueba E2E completa');

    // Step 5: Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Step 6: Wait for server response and UI update
    await page.waitForTimeout(3000);

    // Step 7: Verify form was closed
    const formClosed = await formOverlay.count();
    expect(formClosed).toBe(0);

    // Step 8: Verify trips section still exists
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // Step 9: VALIDATE - Get trip cards and verify content
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount({ min: 1, timeout: 10000 });

    // Step 10: VALIDATE - Verify specific trip card contains expected content
    const firstTripCard = tripCards.first();
    const tripCardText = await firstTripCard.textContent();
    expect(tripCardText).toContain('Recurrente');
    expect(tripCardText).toContain('35.0 km');
    expect(tripCardText).toContain('09:30');
  });
});
