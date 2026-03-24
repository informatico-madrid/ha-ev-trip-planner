# Requirements: E2E Tests for Trip CRUD Panel

## Goal
Crear tests E2E completos que verifiquen la funcionalidad de CRUD de viajes desde el panel de control del vehículo en Home Assistant.

## User Stories

### US-1: Panel Loading Test
**As a** test engineer
**I want** to verify the panel loads correctly
**So that** I can confirm vehicle ID extraction works

**Acceptance Criteria:**
- [ ] AC-1.1: Panel loads at URL `/ev-trip-planner-{vehicle_id}`
- [ ] AC-1.2: Panel loads at URL `/panel/ev-trip-planner-{vehicle_id}`
- [ ] AC-1.3: Vehicle ID is correctly extracted from URL
- [ ] AC-1.4: Panel header shows vehicle name

### US-2: Trip List Loading Test
**As a** test engineer
**I want** to verify trips load from the trip_list service
**So that** I can confirm service integration works

**Acceptance Criteria:**
- [ ] AC-2.1: Panel displays "No hay viajes" when no trips exist
- [ ] AC-2.2: Panel displays trip count when trips exist
- [ ] AC-2.3: Recurring trips are displayed with correct format
- [ ] AC-2.4: Punctual trips are displayed with correct format

### US-3: Create Trip Test
**As a** test engineer
**I want** to verify trip creation workflow
**So that** I can confirm trip_create service integration works

**Acceptance Criteria:**
- [ ] AC-3.1: Clicking "+ Agregar Viaje" opens form modal
- [ ] AC-3.2: Form shows all required fields (type, day, time)
- [ ] AC-3.3: Selecting "Recurrente" shows day selector
- [ ] AC-3.4: Selecting "Puntual" hides day selector
- [ ] AC-3.5: Filling form and clicking submit creates trip
- [ ] AC-3.6: Form closes after successful creation
- [ ] AC-3.7: New trip appears in trip list immediately

### US-4: Edit Trip Test
**As a** test engineer
**I want** to verify trip editing workflow
**So that** I can confirm trip_update service integration works

**Acceptance Criteria:**
- [ ] AC-4.1: Clicking "Editar" on a trip opens form
- [ ] AC-4.2: Form is pre-filled with existing trip data
- [ ] AC-4.3: Modifying trip fields and submitting updates trip
- [ ] AC-4.4: Updated trip displays with new values

### US-5: Delete Trip Test
**As a** test engineer
**I want** to verify trip deletion workflow
**So that** I can confirm delete_trip service integration works

**Acceptance Criteria:**
- [ ] AC-5.1: Clicking "Eliminar" shows confirmation dialog
- [ ] AC-5.2: Confirming deletion removes trip from list
- [ ] AC-5.3: Canceling deletion keeps trip in list

### US-6: Pause/Resume Recurring Trip Test
**As a** test engineer
**I want** to verify pause/resume workflow
**So that** I can confirm pause_recurring_trip and resume_recurring_trip services work

**Acceptance Criteria:**
- [ ] AC-6.1: Clicking "Pausar" on active trip pauses it
- [ ] AC-6.2: Paused trip shows as inactive
- [ ] AC-6.3: Clicking "Reanudar" on paused trip resumes it
- [ ] AC-6.4: Resumed trip shows as active again

### US-7: Complete/Cancel Punctual Trip Test
**As a** test engineer
**I want** to verify complete/cancel workflow
**So that** I can confirm complete_punctual_trip and cancel_punctual_trip services work

**Acceptance Criteria:**
- [ ] AC-7.1: Clicking "Completar" on punctual trip marks it complete
- [ ] AC-7.2: Completed trip is removed from active list
- [ ] AC-7.3: Clicking "Cancelar" on active punctual trip cancels it
- [ ] AC-7.4: Cancelled trip is removed from list

## Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Panel loads at correct URL | High |
| FR-2 | Vehicle ID extracted from URL | High |
| FR-3 | Trip list service returns data | High |
| FR-4 | Create trip modal opens | High |
| FR-5 | Trip creation service works | High |
| FR-6 | Edit trip modal pre-fills data | High |
| FR-7 | Trip update service works | High |
| FR-8 | Delete confirmation dialog | High |
| FR-9 | Delete trip service works | High |
| FR-10 | Pause/Resume services work | High |
| FR-11 | Complete/Cancel services work | High |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test execution time | Total tests | < 5 minutes |
| NFR-2 | Test reliability | Pass rate | 100% |
| NFR-3 | Browser support | Browsers | Chrome, Firefox, Safari |
| NFR-4 | HA version compatibility | Versions | 2024.x, 2025.x |

## Test Strategy

### Browser-Based Tests (New)
Tests that interact with the actual panel in a browser:
- Navigate to panel URL
- Click buttons
- Fill forms
- Verify UI changes

### Static Code Analysis (Existing)
Tests that verify code structure:
- Check methods exist
- Verify service calls
- Validate response handling

## Out of Scope

- Testing the backend EV Trip Planner integration logic
- Testing HA core functionality
- Performance testing
- Load testing

## Dependencies

- Home Assistant instance running
- EV Trip Planner integration installed
- Vehicle configured in HA
- Service calls available (trip_list, trip_create, etc.)

## Success Criteria

- [ ] All 7 user stories implemented with browser tests
- [ ] Tests pass in Chrome, Firefox, Safari
- [ ] Tests run in < 5 minutes total
- [ ] No flaky tests (consistent pass rate)
- [ ] Tests can run in CI/CD pipeline
