/**
 * E2E Test: Real interactive flow for creating a trip with Backend Validation
 *
 * IMPORTANT: Tests MUST verify actual backend state changes, not just UI behavior.
 * This test validates complete trip creation flow through backend API calls.
 *
 * Usage:
 *   npx playwright test test-create-trip-flow.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';

// Helper to fetch trips from backend via service call
async function fetchTripsFromBackend(page: any, vehicle: string) {
  const response = await page.request.post(`${haUrl}/api/services/ev_trip_planner/trip_list`, {
    data: { service_data: { vehicle_id: vehicle } }
  });
  return await response.json();
}

test.describe('Create Trip Flow - COMPLETO VALIDACION BACKEND', () => {

  // ============================================
  // CREATE - Validar creación de viajes recurrentes
  // ============================================

  test('should create a recurring trip through real user interaction and verify backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // STEP 1: Click the "Agregar Viaje" button
    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripBtn).toBeVisible({ timeout: 10000 });
    await addTripBtn.click();

    // STEP 2: Wait for the form overlay to appear
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // STEP 3: Fill out the trip form fields
    const tripTypeSelect = page.locator('ev-trip-planner-panel >> #trip-type');
    await tripTypeSelect.selectOption('recurrente');

    const tripDaySelect = page.locator('ev-trip-planner-panel >> #trip-day');
    await tripDaySelect.selectOption('1');

    const timeInput = page.locator('ev-trip-planner-panel >> #trip-time');
    await timeInput.fill('08:00');

    const kmInput = page.locator('ev-trip-planner-panel >> #trip-km');
    await kmInput.fill('25.5');

    const kwhInput = page.locator('ev-trip-planner-panel >> #trip-kwh');
    await kwhInput.fill('5.2');

    const descriptionTextarea = page.locator('ev-trip-planner-panel >> #trip-description');
    await descriptionTextarea.fill('Viaje al trabajo');

    // STEP 4: Click the submit button
    const submitBtn = page.locator('ev-trip-planner-panel >> button[type="submit"]');
    await submitBtn.click();

    // STEP 5: Wait for form to close
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // STEP 6: CRITICAL - Verify trip was actually created in BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedCount = updatedResponse?.result?.recurring_trips?.length || 0;

    // Backend MUST have created at least 1 new trip
    expect(updatedCount).toBe(initialCount + 1,
      'Backend should have created a new recurring trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.result.recurring_trips.find(
      (t: any) => t.descripcion === 'Viaje al trabajo'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.dia_semana).toBe('1', 'Day should be Monday');
    expect(newTrip.hora).toBe('08:00', 'Time should be 08:00');
    expect(newTrip.km).toBe(25.5, 'Distance should be 25.5 km');

    // STEP 7: VALIDATE - The form should be closed (overlay removed)
    const formStillVisible = await formOverlay.count();
    expect(formStillVisible).toBe(0);

    // STEP 8: VALIDATE - Check that trips list section exists
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // STEP 9: VALIDATE - Check for trips-list element
    const tripsList = page.locator('ev-trip-planner-panel >> .trips-list');
    await expect(tripsList).toBeVisible({ timeout: 10000 });

    // STEP 10: VALIDATE - Check that trip cards appear in the list matching backend
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedCount, { timeout: 10000 });

    // STEP 11: VALIDATE - Verify trip card contains expected content from backend
    const firstTripCard = tripCards.first();
    await expect(firstTripCard).toBeVisible();

    const tripCardText = await firstTripCard.textContent();
    expect(tripCardText).toContain('Recurrente');
    expect(tripCardText).toContain('25.5 km');
    expect(tripCardText).toContain('Lunes');
    expect(tripCardText).toContain('08:00');
  });

  // ============================================
  // CREATE - Validar creación de viajes puntuales
  // ============================================

  test('should create a punctual trip through real user interaction and verify backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualCount = initialResponse?.result?.punctual_trips?.length || 0;

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

    // STEP 5: Wait for form to close
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // STEP 6: CRITICAL - Verify trip was actually created in BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualCount = updatedResponse?.result?.punctual_trips?.length || 0;

    // Backend MUST have created at least 1 new punctual trip
    expect(updatedPunctualCount).toBe(initialPunctualCount + 1,
      'Backend should have created a new punctual trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.result.punctual_trips.find(
      (t: any) => t.descripcion === 'Viaje a la playa'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.datetime).toContain('2026-03-25', 'Date should be 2026-03-25');
    expect(newTrip.datetime).toContain('10:00', 'Time should be 10:00');

    // STEP 7: VALIDATE - Form should be closed
    const formStillVisible = await formOverlay.count();
    expect(formStillVisible).toBe(0);

    // STEP 8: VALIDATE - Check trips list exists
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // STEP 9: VALIDATE - Check for trip cards
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedPunctualCount, { timeout: 10000 });

    // STEP 10: VALIDATE - Verify trip card content
    const firstTripCard = tripCards.first();
    const tripCardText = await firstTripCard.textContent();
    expect(tripCardText).toContain('Puntual');
    expect(tripCardText).toContain('50.0 km');
  });

  // ============================================
  // UPDATE - Validar edición de viajes
  // ============================================

  test('should edit an existing trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to edit');
      return;
    }

    const tripId = initialTrips[0].id;
    const originalTime = initialTrips[0].hora;
    const originalKm = initialTrips[0].km;

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

      // STEP 3: Verify form is pre-filled with original data from backend
      const editTimeInput = page.locator('ev-trip-planner-panel >> #trip-time');
      await expect(editTimeInput).toHaveValue(originalTime);

      const editKmInput = page.locator('ev-trip-planner-panel >> #trip-km');
      await expect(editKmInput).toHaveValue(String(originalKm));

      // STEP 4: Modify the trip time
      const newTime = '14:30';
      await editTimeInput.fill(newTime);

      // STEP 5: Modify the distance
      const newKm = '40.0';
      await editKmInput.fill(newKm);

      // STEP 6: Submit the edit
      const saveBtn = page.locator('ev-trip-planner-panel >> button[type="submit"]');
      await saveBtn.click();

      // STEP 7: Wait for form to close
      await expect(editFormOverlay).toBeHidden({ timeout: 10000 });

      // STEP 8: CRITICAL - Verify backend was actually updated
      const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
      const updatedTrips = updatedResponse?.result?.recurring_trips || [];

      const updatedTrip = updatedTrips.find((t: any) => t.id === tripId);

      expect(updatedTrip).toBeDefined('Trip should exist in backend after edit');
      expect(updatedTrip.hora).toBe(newTime, 'Backend should have updated time');
      expect(updatedTrip.km).toBe(parseFloat(newKm), 'Backend should have updated km');

      // STEP 9: VALIDATE - Form should be closed
      const formStillVisible = await editFormOverlay.count();
      expect(formStillVisible).toBe(0);

      // STEP 10: VALIDATE - Check trips list is updated
      const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
      await expect(tripsSection).toBeVisible({ timeout: 10000 });

      // STEP 11: VALIDATE - Verify trip card contains updated content from backend
      const tripCardsAfterEdit = page.locator('ev-trip-planner-panel >> .trip-card');
      await expect(tripCardsAfterEdit).toHaveCount(updatedTrips.length, { timeout: 10000 });

      const tripCardText = await tripCards.first().textContent();
      expect(tripCardText).toContain('40.0 km');
      expect(tripCardText).toContain('14:30');
    } else {
      test.skip('No existing trips to edit');
    }
  });

  // ============================================
  // DELETE - Validar cancelación de creación
  // ============================================

  test('should cancel trip creation and verify backend unchanged', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

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
    await expect(formOverlay).toBeHidden({ timeout: 5000 });

    // STEP 6: CRITICAL - Verify backend is unchanged (no trip created)
    const response = await fetchTripsFromBackend(page, vehicleId);
    const currentCount = response?.result?.recurring_trips?.length || 0;

    expect(currentCount).toBe(initialCount, 'Backend should not create trip when user cancels');
  });

  // ============================================
  // COMPLETE FLOW - Validar flujo completo CRUD
  // ============================================

  test('should complete full trip creation workflow with backend validation', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Wait for panel to be ready
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Step 1: Verify initial state - trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // Step 2: Get initial trip count from backend
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // Step 3: Click add trip button
    const addTripBtn = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await addTripBtn.click();

    // Step 4: Form appears - verify form overlay is visible
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Step 5: Fill all form fields
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('3');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('09:30');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('35.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('7.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Prueba E2E completa');

    // Step 6: Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Step 7: Wait for form to close
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // Step 8: CRITICAL - Verify backend was actually updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedCount = updatedResponse?.result?.recurring_trips?.length || 0;

    expect(updatedCount).toBe(initialCount + 1,
      'Backend should have created a new trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.result.recurring_trips.find(
      (t: any) => t.descripcion === 'Prueba E2E completa'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.dia_semana).toBe('3', 'Day should be Wednesday');
    expect(newTrip.hora).toBe('09:30', 'Time should be 09:30');
    expect(newTrip.km).toBe(35.0, 'Distance should be 35.0 km');

    // Step 9: Verify form was closed
    const formClosed = await formOverlay.count();
    expect(formClosed).toBe(0);

    // Step 10: Verify trips section still exists
    await expect(tripsSection).toBeVisible({ timeout: 10000 });

    // Step 11: VALIDATE - Get trip cards and verify content matches backend
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedCount, { timeout: 10000 });

    // Step 12: VALIDATE - Verify specific trip card contains expected content from backend
    const firstTripCard = tripCards.first();
    const tripCardText = await firstTripCard.textContent();
    expect(tripCardText).toContain('Recurrente');
    expect(tripCardText).toContain('35.0 km');
    expect(tripCardText).toContain('09:30');
  });
});
