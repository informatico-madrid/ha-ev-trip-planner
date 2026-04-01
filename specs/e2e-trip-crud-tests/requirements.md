# Requirements: E2E Trip CRUD Tests

## Goal

Create Playwright E2E tests that verify the complete CRUD lifecycle of trips (Create, Edit, Delete) for a configured vehicle in the EV Trip Planner panel. Tests interact through Shadow DOM with real user workflows and validate that trips persist correctly in the trip list.

## User Stories

### US-1: Create Recurring Trip

**As a** vehicle owner
**I want to** create a recurring trip with day, time, distance, and energy values
**So that** I can schedule repeated weekly trips for my commute

**Acceptance Criteria:**
- [ ] AC-1.1: Clicking ".add-trip-btn" opens the trip form modal
- [ ] AC-1.2: Selecting "recurrente" reveals day selector (#trip-day) and time selector (#trip-time)
- [ ] AC-1.3: Day selector (#trip-day) accepts values 0-6 (Sunday-Saturday)
- [ ] AC-1.4: Time selector (#trip-time) accepts 24h time format
- [ ] AC-1.5: Distance field (#trip-km) accepts numeric values with 0.1 step
- [ ] AC-1.6: Energy field (#trip-kwh) accepts numeric values with 0.1 step
- [ ] AC-1.7: Description field (#trip-description) accepts free text
- [ ] AC-1.8: Submitting form with "Crear Viaje" button creates the trip
- [ ] AC-1.9: Form closes after successful creation
- [ ] AC-1.10: New recurring trip appears in .trips-list with correct day/time/km values
- [ ] AC-1.11: Trip card has unique data-trip-id attribute

### US-2: Create Punctual Trip

**As a** vehicle owner
**I want to** create a one-time trip with a specific datetime and distance
**So that** I can plan an irregular trip outside my regular schedule

**Acceptance Criteria:**
- [ ] AC-2.1: Clicking ".add-trip-btn" opens the trip form modal
- [ ] AC-2.2: Selecting "puntual" reveals datetime selector (#trip-datetime) instead of day/time
- [ ] AC-2.3: DateTime selector (#trip-datetime) accepts ISO datetime-local format
- [ ] AC-2.4: Distance field (#trip-km) accepts numeric values
- [ ] AC-2.5: Energy field (#trip-kwh) accepts numeric values
- [ ] AC-2.6: Submitting form with "Crear Viaje" button creates the trip
- [ ] AC-2.7: New punctual trip appears in .trips-list with correct datetime/km values
- [ ] AC-2.8: Trip card shows punctual indicator (not showing day-of-week)

### US-3: Edit Trip

**As a** vehicle owner
**I want to** modify an existing trip's details
**So that** I can correct mistakes or update my schedule

**Acceptance Criteria:**
- [ ] AC-3.1: Clicking ".trip-action-btn.edit-btn" on a trip card opens edit form
- [ ] AC-3.2: Edit form pre-fills all existing trip values (type, day/time or datetime, km, kwh, description)
- [ ] AC-3.3: Submit button text changes to "Guardar Cambios"
- [ ] AC-3.4: Modifying km or time and submitting saves the changes
- [ ] AC-3.5: Edited trip reflects new values in the .trips-list immediately
- [ ] AC-3.6: Clicking ".btn.btn-secondary" (Cancelar) discards changes and closes form

### US-4: Delete Trip

**As a** vehicle owner
**I want to** delete an unwanted trip
**So that** I can remove trips I no longer need

**Acceptance Criteria:**
- [ ] AC-4.1: Clicking ".trip-action-btn.delete-btn" triggers browser confirmation dialog
- [ ] AC-4.2: Accepting confirmation removes trip from .trips-list
- [ ] AC-4.3: Dismissing confirmation keeps trip in .trips-list unchanged
- [ ] AC-4.4: Deleted trip no longer appears in the list (data-trip-id removed)
- [ ] AC-4.5: Empty state (.no-trips) shows if last trip is deleted

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Panel loads at /ev-trip-planner-{vehicle_id} | High | URL matches pattern, panel renders |
| FR-2 | Shadow DOM traversal works | High | ev-trip-planner-panel >> .selector finds elements |
| FR-3 | Recurring trip creation | High | AC-1.1 through AC-1.11 verified |
| FR-4 | Punctual trip creation | High | AC-2.1 through AC-2.8 verified |
| FR-5 | Trip editing | High | AC-3.1 through AC-3.6 verified |
| FR-6 | Trip deletion with confirmation | High | AC-4.1 through AC-4.5 verified |
| FR-7 | Form validation | Medium | Required fields enforced before submit |
| FR-8 | Form cancel/discard | Medium | Cancel button closes form without changes |
| FR-9 | Trip list updates reactively | High | New trips appear immediately after submit |
| FR-10 | Independent test data | High | Each test creates and cleans up its own trips |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Execution time | Total test suite | < 5 minutes |
| NFR-2 | Reliability | Pass rate | 100% (no flakes) |
| NFR-3 | Browser support | Chromium | Latest stable |
| NFR-4 | Auth state | Reused via storageState | Consistent login across tests |
| NFR-5 | Test independence | Data isolation | No shared state between tests |

## Glossary

- **Shadow DOM**: Browser encapsulation in Lit web components - selectors must pierce via `ev-trip-planner-panel >> selector`
- **Recurring trip**: Weekly repeating trip with day (0-6) and time fields
- **Punctual trip**: One-time trip with specific datetime field
- **storageState**: Playwright artifact containing encrypted auth cookies for session reuse
- **Config Flow**: Home Assistant integration setup wizard dialog

## Out of Scope

- Testing pause/resume functionality for recurring trips
- Testing complete/cancel for punctual trips
- Testing the backend service integration directly
- Multi-vehicle scenarios
- Performance/load testing
- Cross-browser testing (Firefox, Safari)
- Mobile viewport testing

## Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Home Assistant test-ha | Running HA instance | localhost:8123 |
| auth.setup.ts | Login + Config Flow + storageState | Must pass before tests run |
| EV Trip Planner integration | Panel UI to test | Vehicle "Coche2" configured |
| Playwright chromium | Browser automation | Only chromium required |
| tests/e2e/global.setup.ts | Ephemeral HA server lifecycle | Manages test-ha Docker |

## Verification Contract

**Entry points:**
- `npx playwright test e2e-trip-crud-tests/auth.setup.ts` - runs first to authenticate
- `npx playwright test e2e-trip-crud-tests/trips.spec.ts` - runs CRUD tests
- Panel URL: `http://localhost:8123/ev-trip-planner-Coche2`

**Observable signals:**

*US-1/2 PASS:*
- Form closes after submit
- .trips-list contains .trip-card with data-trip-id
- Card shows correct type label ("Recurrente" or "Puntual")
- Card shows correct day/time or datetime
- Card shows correct km/kwh values

*US-1/2 FAIL:*
- Form shows validation errors
- Trip does not appear in list after 5s wait
- Error notification appears

*US-3 PASS:*
- Edit form opens with pre-filled values
- After edit, .trip-card reflects new values
- "Guardar Cambios" button text visible during edit

*US-3 FAIL:*
- Form not pre-filled (values show placeholder or empty)
- Values unchanged after save

*US-4 PASS:*
- Confirmation dialog appears (browser alert)
- After accept, .trip-card with specific data-trip-id is removed
- .no-trips shows if list becomes empty

*US-4 FAIL:*
- No confirmation dialog
- Trip remains in list after "delete" click
- data-trip-id still present

**Hard invariants:**
- Auth session remains valid throughout test file
- Vehicle "Coche2" remains configured in HA
- No test modifies another test's trips (independent cleanup)
- Panel URL pattern is /ev-trip-planner-Coche2 (not /panel/ev-trip-planner-Coche2)

**Seed data:**
- Vehicle "Coche2" configured via auth.setup.ts Config Flow
- Vehicle has battery_capacity=75, charging_power=11, consumption=0.17, safety_margin=15
- No pre-existing trips (each test creates its own)

**Dependency map:**
- auth.setup.ts writes panel URL to `playwright/.auth/panel-url.txt`
- global.setup.ts manages test-ha Docker container lifecycle
- EV Trip Planner integration provides the web component

**Escalate if:**
- Browser confirmation dialog does not appear on delete (possible HA/panel regression)
- Shadow DOM selectors stop working (web component changed)
- Auth.setup.ts fails (blocks all subsequent tests)

## Success Criteria

- [ ] 4 user stories implemented as Playwright tests
- [ ] All tests pass on first run (no retries)
- [ ] Total execution time < 5 minutes
- [ ] Tests run in CI pipeline via `npx playwright test`
- [ ] Each test cleans up its own created trips
- [ ] Tests use Shadow DOM traversal pattern correctly
