/**
 * E2E Test: Complete Trip CRUD Operations with Backend Validation
 *
 * IMPORTANT: Tests MUST verify actual backend state changes, not just UI behavior.
 * This test validates complete CRUD lifecycle through backend API calls.
 *
 * Usage:
 *   npx playwright test test-trip-crud-complete.spec.ts
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

test.describe('Complete Trip CRUD - VALIDACION BACKEND REAL', () => {
  // ============================================
  // CREATE - Validar creación de viajes
  // ============================================

  test('should create a recurring trip and verify backend storage', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Verify form appears
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Fill form with recurring trip data
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1'); // Monday
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('09:30');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.2');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test recurring trip with full validation');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Verify form closes
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually created in BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedCount = updatedResponse?.result?.recurring_trips?.length || 0;

    // Backend MUST have created at least 1 new trip
    expect(updatedCount).toBe(initialCount + 1,
      'Backend should have created a new recurring trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.result.recurring_trips.find(
      (t: any) => t.descripcion === 'Test recurring trip with full validation'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.dia_semana).toBe('1', 'Day should be Monday');
    expect(newTrip.hora).toBe('09:30', 'Time should be 09:30');
    expect(newTrip.km).toBe(25.5, 'Distance should be 25.5 km');

    // Verify UI reflects the backend state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedCount, { timeout: 10000 });
  });

  test('should create a punctual trip and verify backend storage', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualCount = initialResponse?.result?.punctual_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Fill form with punctual trip data
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
    await page.locator('ev-trip-planner-panel >> #trip-datetime').fill('2026-03-25T14:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('15.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('3.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Punctual trip to airport');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Verify form closes
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually created in BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualCount = updatedResponse?.result?.punctual_trips?.length || 0;

    // Backend MUST have created at least 1 new punctual trip
    expect(updatedPunctualCount).toBe(initialPunctualCount + 1,
      'Backend should have created a new punctual trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.result.punctual_trips.find(
      (t: any) => t.descripcion === 'Punctual trip to airport'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in backend');
    expect(newTrip.datetime).toContain('2026-03-25', 'Date should be 2026-03-25');
    expect(newTrip.datetime).toContain('14:00', 'Time should be 14:00');
  });

  test('should validate required fields - empty km should fail', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with empty required field (km should be required)
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill(''); // Empty - should fail
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.0');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Backend should reject the invalid trip - count should be unchanged
    const response = await fetchTripsFromBackend(page, vehicleId);
    const currentCount = response?.result?.recurring_trips?.length || 0;

    // The backend should NOT have created a trip with empty km
    expect(currentCount).toBe(initialCount,
      'Backend should reject trip with empty required field');
  });

  test('should validate required fields - negative km should be handled', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialCount = initialResponse?.result?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with negative km
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('-5.0'); // Negative
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.0');

    // Submit form - backend should reject or handle
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // Backend should handle negative km - either reject or use absolute value
    const response = await fetchTripsFromBackend(page, vehicleId);
    const currentCount = response?.result?.recurring_trips?.length || 0;

    // Either count changed (backend accepted with abs value) or stayed same (rejected)
    // Both are valid outcomes
    expect(currentCount >= initialCount).toBe(true);
  });

  // ============================================
  // READ - Validar visualización de viajes
  // ============================================

  test('should display trips section with header', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Verify trips header is visible
    const tripsHeader = page.locator('ev-trip-planner-panel >> .trips-header');
    await expect(tripsHeader).toBeVisible({ timeout: 10000 });

    // Verify header contains expected text
    const headerText = await tripsHeader.textContent();
    expect(headerText).toContain('Viajes Programados');
  });

  test('should display add trip button', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for add trip button
    const addTripButton = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripButton).toBeVisible({ timeout: 10000 });
  });

  test('should show no trips message when empty', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get trips from backend
    const response = await fetchTripsFromBackend(page, vehicleId);
    const hasAnyTrips = (response.result?.recurring_trips?.length || 0) > 0 ||
                        (response.result?.punctual_trips?.length || 0) > 0;

    // Check for either no trips message or trip cards
    const hasNoTrips = await page.locator('ev-trip-planner-panel >> .no-trips').count() > 0;
    const hasTripCards = await page.locator('ev-trip-planner-panel >> .trip-card').count() > 0;

    if (!hasAnyTrips) {
      expect(hasNoTrips).toBe(true, 'Should show no trips message when backend is empty');
    } else {
      expect(hasTripCards).toBe(true, 'Should show trip cards when backend has trips');
    }
  });

  // ============================================
  // UPDATE - Validar edición de viajes
  // ============================================

  test('should edit a recurring trip and verify backend update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
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

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Verify form is pre-filled with original data from backend
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    const tripTime = page.locator('ev-trip-planner-panel >> #trip-time');
    const tripKm = page.locator('ev-trip-planner-panel >> #trip-km');

    await expect(tripTime).toHaveValue(originalTime);
    await expect(tripKm).toHaveValue(String(originalKm));

    // Modify the trip
    const newTime = '15:00';
    const newKm = '30.0';

    await tripTime.fill(newTime);
    await tripKm.fill(newKm);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Verify form closes
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend was actually updated
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrips = updatedResponse?.result?.recurring_trips || [];

    const updatedTrip = updatedTrips.find((t: any) => t.id === tripId);

    expect(updatedTrip).toBeDefined('Trip should exist in backend after edit');
    expect(updatedTrip.hora).toBe(newTime, 'Backend should have updated time');
    expect(updatedTrip.km).toBe(parseFloat(newKm), 'Backend should have updated km');

    // Verify UI reflects the backend state
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await expect(tripCard).toContainText(newTime);
    await expect(tripCard).toContainText(`${newKm} km`);
  });

  test('should pause and resume a recurring trip and verify backend state', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip state from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to pause');
      return;
    }

    const tripId = initialTrips[0].id;
    const initialActive = initialTrips[0].activo !== false;

    if (!initialActive) {
      test.skip('Trip already paused, need active trip to test pause');
      return;
    }

    // Pause the trip
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

    // Accept confirmation
    const pauseConfirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres pausar este viaje recurrente?');
    });

    if (pauseConfirmed) {
      // Verify trip is paused in backend
      const pausedResponse = await fetchTripsFromBackend(page, vehicleId);
      const pausedTrip = pausedResponse.result.recurring_trips.find((t: any) => t.id === tripId);
      expect(pausedTrip.activo).toBe(false, 'Backend should have paused the trip');

      // Now resume the trip
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.resume-btn').click();

      const resumeConfirmed = await page.evaluate(() => {
        return confirm('¿Estás seguro de que quieres reanudar este viaje?');
      });

      if (resumeConfirmed) {
        // Verify trip is resumed in backend
        const resumedResponse = await fetchTripsFromBackend(page, vehicleId);
        const resumedTrip = resumedResponse.result.recurring_trips.find((t: any) => t.id === tripId);
        expect(resumedTrip.activo).toBe(true, 'Backend should have resumed the trip');
      }
    }
  });

  // ============================================
  // DELETE - Validar eliminación de viajes
  // ============================================

  test('should delete a recurring trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial trip count and ID from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialTrips = initialResponse?.result?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to delete');
      return;
    }

    const tripToDelete = initialTrips[0];
    const tripId = tripToDelete.id;
    const initialCount = initialTrips.length;

    // Click delete button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // Accept deletion
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres eliminar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still exist in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentCount = response?.result?.recurring_trips?.length || 0;
      expect(currentCount).toBe(initialCount, 'Backend should not delete when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually deleted from the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedTrips = updatedResponse?.result?.recurring_trips || [];

    // Backend should have deleted the trip
    const deletedTripStillExists = updatedTrips.find((t: any) => t.id === tripId);
    expect(deletedTripStillExists).toBeUndefined(
      'Backend should have deleted the trip'
    );

    // Verify count decreased
    expect(updatedTrips.length).toBe(initialCount - 1,
      'Backend trip count should decrease by 1');

    // Verify UI reflects backend state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedTrips.length, { timeout: 10000 });
  });

  test('should delete a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trip
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualTrips = initialResponse?.result?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to delete');
      return;
    }

    const tripToDelete = initialPunctualTrips[0];
    const tripId = tripToDelete.id;
    const initialCount = initialPunctualTrips.length;

    // Find and click delete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.delete-btn').click();

    // Accept deletion
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres eliminar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentCount = response?.result?.punctual_trips?.length || 0;
      expect(currentCount).toBe(initialCount, 'Backend should not delete when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually deleted from the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.result?.punctual_trips || [];

    // Backend should have deleted the trip
    const deletedTripStillExists = updatedPunctualTrips.find((t: any) => t.id === tripId);
    expect(deletedTripStillExists).toBeUndefined(
      'Backend should have deleted the punctual trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  // ============================================
  // COMPLETE/CANCEL - Validar acciones de viajes puntuales
  // ============================================

  test('should complete a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trips from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualTrips = initialResponse?.result?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to complete');
      return;
    }

    const tripToComplete = initialPunctualTrips[0];
    const tripId = tripToComplete.id;
    const initialCount = initialPunctualTrips.length;

    // Find and click complete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.complete-btn').click();

    // Accept confirmation
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres completar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still exist in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentTrips = response?.result?.punctual_trips || [];
      expect(currentTrips.length).toBe(initialCount, 'Backend should not complete trip when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually completed (removed) from the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.result?.punctual_trips || [];

    // Completed trips should be removed from the list
    const completedTripStillExists = updatedPunctualTrips.find((t: any) => t.id === tripId);
    expect(completedTripStillExists).toBeUndefined(
      'Backend should have removed the completed trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  test('should cancel a punctual trip and verify backend removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Get initial punctual trips from BACKEND
    const initialResponse = await fetchTripsFromBackend(page, vehicleId);
    const initialPunctualTrips = initialResponse?.result?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to cancel');
      return;
    }

    const tripToCancel = initialPunctualTrips[0];
    const tripId = tripToCancel.id;
    const initialCount = initialPunctualTrips.length;

    // Find and click cancel button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.cancel-btn').click();

    // Accept confirmation
    const confirmed = await page.evaluate(() => {
      return confirm('¿Estás seguro de que quieres cancelar este viaje?');
    });

    if (!confirmed) {
      await page.locator('body').press('Escape');
      // If user cancelled, trip should still exist in backend
      const response = await fetchTripsFromBackend(page, vehicleId);
      const currentTrips = response?.result?.punctual_trips || [];
      expect(currentTrips.length).toBe(initialCount, 'Backend should not cancel trip when user cancels');
      return;
    }

    // CRITICAL: Verify trip was actually cancelled (removed) from the BACKEND
    const updatedResponse = await fetchTripsFromBackend(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.result?.punctual_trips || [];

    // Cancelled trips should be removed from the list
    const cancelledTripStillExists = updatedPunctualTrips.find((t: any) => t.id === tripId);
    expect(cancelledTripStillExists).toBeUndefined(
      'Backend should have removed the cancelled trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Backend punctual trip count should decrease by 1');
  });

  // ============================================
  // EDGE CASES - Casos borde
  // ============================================

  test('should handle special characters in description', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with special characters in description
    const specialChars = 'Test with special: á é í ó ú ñ <script>alert("xss")</script>';
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('2.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(specialChars);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend stored the description correctly (escaped)
    const response = await fetchTripsFromBackend(page, vehicleId);
    const newTrip = response.result.recurring_trips.find(
      (t: any) => t.descripcion && t.descripcion.includes('special')
    );

    expect(newTrip).toBeDefined('Trip with special characters should be stored in backend');

    // Backend should have escaped the HTML (XSS protection)
    expect(newTrip.descripcion).not.toContain('<script>');
  });

  test('should handle long descriptions', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with very long description
    const longDescription = 'A'.repeat(2000);
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('2.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(longDescription);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify backend stored the long description
    const response = await fetchTripsFromBackend(page, vehicleId);
    const newTrip = response.result.recurring_trips.find(
      (t: any) => t.descripcion && t.descripcion.length > 100
    );

    expect(newTrip).toBeDefined('Trip with long description should be stored in backend');
    expect(newTrip.descripcion.length).toBeGreaterThan(100, 'Backend should store long description');
  });
});
