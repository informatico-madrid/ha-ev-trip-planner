# Trip Creation - Implementation Tasks

## Overview

This document contains the implementation tasks for the trip creation feature. The tasks follow a POC-first approach with 4 phases:

- **Phase 1 (POC)**: Core functionality works
- **Phase 2 (Refactor)**: Code quality improvements
- **Phase 3 (Testing)**: Unit and E2E tests
- **Phase 4 (Quality)**: CI/CD and final polish

---

## Phase 1: POC - Core Functionality

### Task 1.1: Enhance _handleTripCreate with Error Handling

**Description:** Add try-catch-finally pattern to the `_handleTripCreate` function in panel.js to handle service calls properly with loading states.

**Status:** [x] Complete

**Do:**
```javascript
async _handleTripCreate(e) {
  e.preventDefault();

  if (!this._hass || !this._vehicleId) {
    this._showAlert('Error: No hay conexión con Home Assistant', false);
    return;
  }

  const form = e.target;
  const formData = new FormData(form);

  // Extract form data
  const type = formData.get('type');
  const km = formData.get('km');
  const kwh = formData.get('kwh');
  const description = formData.get('description');

  // Build service data
  const serviceData = {
    vehicle_id: this._vehicleId,
    type: type,
  };

  if (type === 'puntual') {
    const datetime = formData.get('datetime');
    if (datetime) {
      serviceData.datetime = datetime;
    }
  } else {
    const day = formData.get('day');
    const time = formData.get('time');
    serviceData.dia_semana = day;
    serviceData.hora = time;
  }

  serviceData.km = parseFloat(km);
  serviceData.kwh = parseFloat(kwh);
  serviceData.description = description || '';

  // Set loading state
  const submitBtn = form.querySelector('.btn-primary');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Creando...';
  submitBtn.disabled = true;

  try {
    await this._hass.callService('ev_trip_planner', 'trip_create', serviceData);
    this._closeForm();
    await this._loadTrips();
    this._showAlert('✅ Viaje creado exitosamente', true);
  } catch (error) {
    console.error('EV Trip Planner Panel: Error creating trip:', error);
    this._showAlert(`❌ Error al crear el viaje: ${error.message}`, false);
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] Function uses try-catch-finally pattern
- [ ] Service call is wrapped in try block
- [ ] Error is caught and displayed with _showAlert
- [ ] Form closes after successful creation
- [ ] Trip list refreshes after creation

**Verify:**
```bash
# Test manually in HA
# 1. Open EV Trip Planner panel
# 2. Click "Add Trip"
# 3. Fill form with valid data
# 4. Submit and verify success message
# 5. Verify trip appears in list
```

**Commit:** `feat: add error handling to trip create`

---

### Task 1.2: Implement Form Validation

**Status:** [x] Complete

**Description:** Add form validation before service call to ensure required fields are present and valid.

**Do:**
```javascript
async _handleTripCreate(e) {
  e.preventDefault();

  const form = e.target;
  const formData = new FormData(form);

  // Extract form data
  const km = formData.get('km');
  const kwh = formData.get('kwh');

  // Validate required fields
  if (!km || parseFloat(km) <= 0) {
    this._showAlert('❌ La distancia (km) debe ser un número positivo', false);
    return;
  }

  if (!kwh || parseFloat(kwh) <= 0) {
    this._showAlert('❌ El consumo de energía (kWh) debe ser un número positivo', false);
    return;
  }

  // Continue with service call...
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] Required field validation added
- [ ] Positive number validation for km/kwh
- [ ] Early return on validation failure
- [ ] User-friendly error messages
- [ ] Form remains open on validation error

**Verify:**
```bash
# Test with empty km field
# Should show validation error and not proceed to service call
```

**Commit:** `feat: add form validation for required fields`

---

### Task 1.3: Implement Edit Mode

**Description:** Add `_handleTripEdit` function to load existing trip data into the form for editing.

**Do:**
```javascript
async _handleTripEdit(tripId) {
  const trip = await this._getTripById(tripId);
  if (!trip) {
    this._showAlert('❌ Error: Viaje no encontrado', false);
    return;
  }

  this._showEditForm(trip);
}

_showEditForm(trip) {
  this._editingTrip = trip;
  this._showForm = true;
  this._formType = trip.type === 'puntual' ? 'puntual' : 'recurrente';
}

async _getTripById(tripId) {
  if (!this._hass || !this._vehicleId) return null;

  try {
    const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    let tripsData = response;
    if (tripsData && tripsData.recurring_trips !== undefined) {
      const allTrips = [
        ...tripsData.recurring_trips.map(t => ({...t, trip_type: 'recurrente'})),
        ...tripsData.punctual_trips.map(t => ({...t, trip_type: 'puntual'})),
      ];
      return allTrips.find(t => t.id === tripId) || null;
    }
    return null;
  } catch (error) {
    console.error('Error fetching trip:', error);
    return null;
  }
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] `_handleTripEdit` function implemented
- [ ] `_getTripById` helper function added
- [ ] Form pre-filled with existing trip data
- [ ] Trip ID stored for update operation
- [ ] Edit mode indicator shown

**Verify:**
```bash
# Click edit button on a trip
# Form should open with pre-filled data
```

**Commit:** `feat: implement edit mode for trips`

---

### Task 1.4: Implement _handleTripUpdate

**Description:** Add service call handler for updating existing trips.

**Do:**
```javascript
async _handleTripUpdate(e) {
  e.preventDefault();

  const form = e.target;
  const formData = new FormData(form);

  const tripId = formData.get('edit-trip-id');
  if (!tripId) {
    this._showAlert('❌ Error: No se pudo identificar el viaje', false);
    return;
  }

  const type = formData.get('type');
  const km = formData.get('km');
  const kwh = formData.get('kwh');

  // Validate
  if (!km || parseFloat(km) <= 0) {
    this._showAlert('❌ La distancia (km) debe ser un número positivo', false);
    return;
  }

  if (!kwh || parseFloat(kwh) <= 0) {
    this._showAlert('❌ El consumo de energía (kWh) debe ser un número positivo', false);
    return;
  }

  // Build service data
  const serviceData = {
    vehicle_id: this._vehicleId,
    trip_id: tripId,
    type: type,
  };

  if (type === 'puntual') {
    serviceData.datetime = formData.get('datetime');
  } else {
    serviceData.dia_semana = formData.get('day');
    serviceData.hora = formData.get('time');
  }

  serviceData.km = parseFloat(km);
  serviceData.kwh = parseFloat(kwh);
  serviceData.description = formData.get('description') || '';

  // Set loading state
  const submitBtn = form.querySelector('.btn-primary');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Guardando...';
  submitBtn.disabled = true;

  try {
    await this._hass.callService('ev_trip_planner', 'trip_update', serviceData);
    this._closeForm();
    await this._loadTrips();
    this._showAlert('✅ Viaje actualizado exitosamente', true);
  } catch (error) {
    console.error('Error updating trip:', error);
    this._showAlert(`❌ Error al actualizar el viaje: ${error.message}`, false);
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] `_handleTripUpdate` function implemented
- [ ] Service data includes trip_id
- [ ] Uses `trip_update` service
- [ ] Success/error handling present
- [ ] Form closes and list refreshes

**Verify:**
```bash
# Test update service
ha service call ev_trip_planner.trip_update '{"trip_id": "xxx", "vehicle_id": "Coche2", "type": "recurrente", "dia_semana": "1", "hora": "10:00", "km": 30.0, "kwh": 6.0, "description": "Updated"}'
```

**Commit:** `feat: implement trip update service call`

---

### Task 1.5: Implement Delete with Confirmation

**Description:** Add delete functionality with confirmation dialog.

**Do:**
```javascript
async _handleDeleteTrip(tripId) {
  if (!confirm('¿Estás seguro de que quieres eliminar este viaje?')) {
    return;
  }

  try {
    await this._hass.callService('ev_trip_planner', 'delete_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    await this._loadTrips();
    this._showAlert('✅ Viaje eliminado exitosamente', true);
  } catch (error) {
    console.error('Error deleting trip:', error);
    this._showAlert(`❌ Error: ${error.message}`, false);
  }
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] Confirmation dialog present
- [ ] Delete service called on confirmation
- [ ] Success/error handling present
- [ ] Trip list refreshes after deletion
- [ ] Cancel button prevents deletion

**Verify:**
```bash
# Click delete button
# Confirm dialog appears
# Confirm deletion
# Trip should be removed from list
```

**Commit:** `feat: add delete with confirmation dialog`

---

### Phase 1 POC Milestone

**What's Working:**
- ✅ Recurring trips can be created
- ✅ Punctual trips can be created
- ✅ Form validation prevents invalid submissions
- ✅ Edit mode pre-fills form with existing data
- ✅ Trips can be updated
- ✅ Trips can be deleted with confirmation
- ✅ Success/error messages displayed
- ✅ Trip list refreshes after CRUD operations

**Verify POC:**
```bash
# Run manual test
ha service call ev_trip_planner.trip_create '{"vehicle_id": "Coche2", "type": "recurrente", "dia_semana": "1", "hora": "09:30", "km": 25.5, "kwh": 5.2, "description": "POC Test"}'

# Check trip appears
ha service call ev_trip_planner.trip_list '{"vehicle_id": "Coche2"}'
```

**Next:** Refactor code quality and add tests

---

## Phase 2: Refactor - Code Quality

### Task 2.1: Extract Service Call Handler

**Description:** Create a reusable service call handler to avoid code duplication.

**Do:**
```javascript
async _callTripService(serviceName, serviceData) {
  try {
    const result = await this._hass.callService('ev_trip_planner', serviceName, serviceData);
    return result;
  } catch (error) {
    console.error(`Service call failed for ${serviceName}:`, error);
    throw error;
  }
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] `_callTripService` method created
- [ ] All service calls use this method
- [ ] Error handling centralized
- [ ] No code duplication

**Verify:**
```bash
# All service calls should use _callTripService
grep -n "_callTripService" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `refactor: extract service call handler`

---

### Task 2.2: Add Form Reset in Finally Block

**Description:** Ensure form is always reset after submission, even on error.

**Do:**
```javascript
finally {
  form.reset(); // Reset form fields
  submitBtn.textContent = originalText;
  submitBtn.disabled = false;
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] Finally block added to all form handlers
- [ ] Form reset in finally
- [ ] Form closes in finally
- [ ] Works on both success and error

**Verify:**
```bash
# Submit form with error
# Form should close and reset
```

**Commit:** `refactor: add form reset in finally block`

---

### Task 2.3: Add Loading State Management

**Description:** Show loading indicator during service calls to prevent duplicate submissions.

**Do:**
```javascript
// Already implemented in Tasks 1.1 and 1.4
// Ensure consistent pattern across all handlers
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`

**Done when:**
- [ ] Loading state added to all handlers
- [ ] Submit button disabled during call
- [ ] Loading text shown
- [ ] State reset in finally block

**Verify:**
```bash
# Submit form
# Button should show loading text
# Button should be disabled
# After completion, button should be re-enabled
```

**Commit:** `refactor: add loading state to prevent duplicate submissions`

---

### Phase 2 Refactor Milestone

**What's Improved:**
- ✅ Service call handler extracted
- ✅ Form reset guaranteed in finally
- ✅ Loading state prevents duplicate submissions
- ✅ No code duplication
- ✅ Better UX with loading indicators

**Next:** Add comprehensive tests

---

## Phase 3: Testing - Unit and E2E

### Task 3.1: Add E2E Tests for Create Trip

**Description:** Create E2E tests for complete trip creation flow.

**Do:**
```typescript
// tests/e2e/test-create-trip.spec.ts
import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner - Create Trip', () => {
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';

  test('should create a recurring trip and verify backend', async ({ page }) => {
    // Navigate to panel
    await page.goto(`/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForSelector('.add-trip-btn', { timeout: 10000 });

    // Click add trip button
    await page.click('.add-trip-btn');

    // Fill form
    await page.selectOption('#trip-type', 'recurrente');
    await page.selectOption('#trip-day', '1');
    await page.fill('#trip-time', '09:30');
    await page.fill('#trip-km', '25.5');
    await page.fill('#trip-kwh', '5.2');
    await page.fill('#trip-description', 'Test trip');

    // Submit
    await page.click('button[type="submit"]');

    // Verify success
    await expect(page.locator('.trip-form-overlay')).toBeHidden({ timeout: 10000 });

    // Verify trip appears in list
    const tripCards = page.locator('.trip-card');
    await expect(tripCards).toHaveCount(1);
  });
});
```

**Files:**
- `tests/e2e/test-create-trip.spec.ts`

**Done when:**
- [ ] E2E tests created
- [ ] Recurring trip test
- [ ] Punctual trip test
- [ ] Backend state verification

**Verify:**
```bash
npx playwright test tests/e2e/test-create-trip.spec.ts -v
```

**Commit:** `test: add E2E tests for trip creation`

---

### Task 3.2: Add E2E Tests for Edit Trip

**Description:** Create E2E tests for edit functionality.

**Do:**
```typescript
// tests/e2e/test-edit-trip.spec.ts
import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner - Edit Trip', () => {
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';

  test('should edit a trip', async ({ page }) => {
    // Navigate to panel
    await page.goto(`/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForSelector('.trip-card', { timeout: 10000 });

    // Click edit button
    await page.click('.trip-card .edit-btn');

    // Verify form is pre-filled
    await expect(page.locator('#trip-km')).toHaveValue('25.5');

    // Modify and save
    await page.fill('#trip-km', '30.0');
    await page.click('button[type="submit"]');

    // Verify update
    await expect(page.locator('.trip-form-overlay')).toBeHidden({ timeout: 10000 });

    // Verify trip list updated
    const tripCards = page.locator('.trip-card');
    await expect(tripCards).toHaveCount(1);
  });
});
```

**Files:**
- `tests/e2e/test-edit-trip.spec.ts`

**Done when:**
- [ ] Edit E2E test created
- [ ] Pre-fill form verified
- [ ] Update functionality tested
- [ ] Backend state verified

**Verify:**
```bash
npx playwright test tests/e2e/test-edit-trip.spec.ts -v
```

**Commit:** `test: add E2E tests for trip edit`

---

### Task 3.3: Add E2E Tests for Delete Trip

**Description:** Create E2E tests for delete functionality.

**Do:**
```typescript
// tests/e2e/test-delete-trip.spec.ts
import { test, expect } from '@playwright/test';

test.describe('EV Trip Planner - Delete Trip', () => {
  const vehicleId = process.env.VEHICLE_ID || 'Coche2';

  test('should delete a trip', async ({ page }) => {
    // Navigate to panel
    await page.goto(`/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Wait for panel to be ready
    await page.waitForSelector('.trip-card', { timeout: 10000 });

    // Get initial count
    const initialCount = await page.locator('.trip-card').count();

    // Click delete button
    await page.click('.trip-card .delete-btn');

    // Confirm
    await page.click('button:has-text("OK")');

    // Verify deletion
    const finalCount = await page.locator('.trip-card').count();
    await expect(finalCount).toBe(initialCount - 1);
  });
});
```

**Files:**
- `tests/e2e/test-delete-trip.spec.ts`

**Done when:**
- [ ] Delete E2E test created
- [ ] Confirmation tested
- [ ] Backend state verified
- [ ] Trip count verified

**Verify:**
```bash
npx playwright test tests/e2e/test-delete-trip.spec.ts -v
```

**Commit:** `test: add E2E tests for trip delete`

---

### Phase 3 Testing Milestone

**What's Tested:**
- ✅ E2E tests for create flow
- ✅ E2E tests for edit flow
- ✅ E2E tests for delete flow
- ✅ Backend state verification
- ✅ Form validation tested

**Next:** Final quality checks

---

## Phase 4: Quality - CI/CD and Polish

### Task 4.1: Add Documentation

**Description:** Add inline documentation and README updates.

**Do:**
```javascript
/**
 * Handle trip creation form submission
 * @param {Event} e - Form submit event
 * @memberof EVTripPlannerPanel
 */
async _handleTripCreate(e) {
  // ... implementation
}
```

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js`
- `README.md`

**Done when:**
- [ ] JSDoc comments added
- [ ] README updated
- [ ] API documented

**Verify:**
```bash
# Check documentation
grep -A 5 "_handleTripCreate" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `docs: add inline documentation`

---

### Task 4.2: Add ESLint Rules

**Description:** Add ESLint rules for consistent code style.

**Do:**
```json
// .eslintrc.json
{
  "rules": {
    "no-console": "warn",
    "prefer-const": "error",
    "no-var": "error",
    "semi": ["error", "always"],
    "quotes": ["error", "single"]
  }
}
```

**Files:**
- `.eslintrc.json`

**Done when:**
- [ ] ESLint configured
- [ ] Rules added
- [ ] Code passes linting

**Verify:**
```bash
npm run lint
```

**Commit:** `chore: add ESLint rules`

---

### Task 4.3: Final Verification and Cleanup

**Description:** Run all tests and verify complete functionality.

**Do:**
```bash
# Run all E2E tests
npx playwright test tests/e2e/ -v

# Check for linting issues
npm run lint

# Verify code coverage
pytest tests/ --cov=custom_components.ev_trip_planner
```

**Files:**
- All test files

**Done when:**
- [ ] All tests pass
- [ ] Linting passes
- [ ] No TODOs remaining
- [ ] Documentation complete

**Verify:**
```bash
# Final verification
echo "=== E2E Tests ==="
npx playwright test tests/e2e/ -v

echo "=== Linting ==="
npm run lint
```

**Commit:** `test: final verification and cleanup`

---

## Phase 4 Quality Milestone

**What's Complete:**
- ✅ Inline documentation added
- ✅ ESLint rules configured
- ✅ All tests passing
- ✅ Linting passes
- ✅ No TODOs remaining

---

## Summary

**Total Tasks:** 11 tasks across 4 phases

**Phase Breakdown:**
- Phase 1 (POC): 5 tasks - proves the idea works (Tasks 1.1-1.5)
- Phase 2 (Refactor): 3 tasks - clean up (Tasks 2.1-2.3)
- Phase 3 (Testing): 3 tasks - add coverage (Tasks 3.1-3.3)
- Phase 4 (Quality): 3 tasks - CI/PR (Tasks 4.1-4.3)

**POC Milestone:** Task 1.5 - All CRUD operations working with error handling

**Implementation Status:** Ready to execute

---

## Execution Notes

### Quick Mode
- All phases executed sequentially
- No intermediate approvals required
- Complete implementation in one session

### Verification
- E2E tests run automatically
- Backend state verified in tests
- No manual intervention needed

### Dependencies
- Home Assistant Core
- Lit web components
- Playwright for E2E testing
