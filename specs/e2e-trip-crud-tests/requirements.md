# Requirements: E2E Trip CRUD Tests

## Goal

Create end-to-end Playwright tests that verify the CRUD functionality (Create, Edit, Delete) for trips in the EV Trip Planner Home Assistant integration. Production code exists and works; only tests are created.

## User Stories

### US-1: Create Recurring Trip

**As a** user  
**I want to** create a recurring weekly trip for my vehicle  
**So that** the system can plan charging schedules around my regular commute

**Acceptance Criteria:**
- [ ] AC-1.1: Navigate to EV Trip Planner panel for vehicle "Coche2"
- [ ] AC-1.2: Click "Add Trip" button and verify form opens
- [ ] AC-1.3: Select trip type "Recurrente" (recurring)
- [ ] AC-1.4: Select a day of the week (e.g., "Lunes")
- [ ] AC-1.5: Enter time (e.g., "08:00")
- [ ] AC-1.6: Enter distance in km (e.g., "25.5")
- [ ] AC-1.7: Enter energy in kWh (e.g., "5.2")
- [ ] AC-1.8: Submit form and verify trip appears in trip list
- [ ] AC-1.9: Verify trip count increases by 1
- [ ] AC-1.10: Trip persists after page reload

### US-2: Create Punctual Trip

**As a** user  
**I want to** create a one-time trip for my vehicle  
**So that** the system can account for an irregular journey

**Acceptance Criteria:**
- [ ] AC-2.1: Navigate to EV Trip Planner panel for vehicle "Coche2"
- [ ] AC-2.2: Click "Add Trip" button and verify form opens
- [ ] AC-2.3: Select trip type "Puntual" (one-time)
- [ ] AC-2.4: Verify day-of-week selector is hidden for punctual trips
- [ ] AC-2.5: Enter date and time via datetime-local input
- [ ] AC-2.6: Enter distance in km (e.g., "50.0")
- [ ] AC-2.7: Enter energy in kWh (e.g., "10.0")
- [ ] AC-2.8: Submit form and verify trip appears in trip list
- [ ] AC-2.9: Verify trip count increases by 1
- [ ] AC-2.10: Trip persists after page reload

### US-3: Edit Trip

**As a** user  
**I want to** edit an existing trip  
**So that** I can update my travel plans when they change

**Acceptance Criteria:**
- [ ] AC-3.1: Navigate to EV Trip Planner panel for vehicle "Coche2"
- [ ] AC-3.2: Verify at least one trip exists (create one if needed)
- [ ] AC-3.3: Click edit button on a trip card
- [ ] AC-3.4: Verify edit form opens with pre-filled values
- [ ] AC-3.5: Modify time (e.g., change from "08:00" to "09:00")
- [ ] AC-3.6: Modify distance (e.g., change from "25.5" to "30.0")
- [ ] AC-3.7: Submit changes and verify form closes
- [ ] AC-3.8: Verify trip card reflects updated values
- [ ] AC-3.9: Changes persist after page reload

### US-4: Delete Trip

**As a** user  
**I want to** delete a trip  
**So that** I can remove trips that are no longer needed

**Acceptance Criteria:**
- [ ] AC-4.1: Navigate to EV Trip Planner panel for vehicle "Coche2"
- [ ] AC-4.2: Verify at least one trip exists (create one if needed)
- [ ] AC-4.3: Record current trip count
- [ ] AC-4.4: Click delete button on a trip card
- [ ] AC-4.5: Handle browser confirmation dialog (accept)
- [ ] AC-4.6: Verify trip is removed from trip list
- [ ] AC-4.7: Verify trip count decreases by 1
- [ ] AC-4.8: Deletion persists after page reload

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Navigate to EV Trip Planner panel | High | Panel loads with `ev-trip-planner-panel` custom element visible |
| FR-2 | Open Add Trip form | High | Form overlay appears with all fields visible |
| FR-3 | Shadow DOM selector traversal | High | All form fields accessible via `ev-trip-planner-panel >> #selector` |
| FR-4 | Create recurring trip | High | Trip saved to backend and appears in UI |
| FR-5 | Create punctual trip | High | Trip saved with datetime and appears in UI |
| FR-6 | Form field validation | Medium | Required fields enforced before submit |
| FR-7 | Open edit form | High | Edit form pre-populated with trip data |
| FR-8 | Update trip | High | Changes saved and reflected in UI |
| FR-9 | Delete trip with confirmation | High | Dialog handled, trip removed from list |
| FR-10 | Trip persistence | High | All CRUD operations survive page reload |
| FR-11 | Test independence | High | Each test cleans up created data |
| FR-12 | Trip count tracking | Medium | `getTripCount()` returns accurate count via Shadow DOM evaluation |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test execution time | seconds per test | < 60s per test |
| NFR-2 | Selector reliability | Shadow DOM access | 100% - no flaky selectors |
| NFR-3 | Dialog handling | page.on('dialog') | Must register before action triggers dialog |
| NFR-4 | Cleanup | Trips removed | All test-created trips deleted in afterEach |
| NFR-5 | Auth state | storageState | Reused across tests via auth.setup.ts |

## Glossary

- **Shadow DOM**: Web Component encapsulated DOM - requires `>>` combinator in Playwright to pierce
- **Ephemeral container**: Temporary Home Assistant instance created by hass-taste-test for testing
- **Config Flow**: Home Assistant integration configuration wizard UI
- **Coche2**: Test vehicle name configured via Config Flow
- **Recurring trip**: Weekly repeating trip with day-of-week and time
- **Punctual trip**: One-time trip with specific date and time
- **storageState**: Playwright authenticated state file for reusing login across tests

## Out of Scope

- Listing/reading trips (implicit - tests verify CRUD but don't explicitly test list pagination)
- Pause/Resume trip functionality
- Trip completion marking
- Multiple vehicle support (tests use only "Coche2")
- Backend API testing (only UI E2E tests)
- Production code changes

## Dependencies

- **auth.setup.ts**: Provides authenticated storageState with "Coche2" configured
- **test-helpers.ts**: TripPanel base class with `navigateToPanel`, `fillTripForm`, `submitTripForm`, `setupDialogHandler`, `getTripCount`
- **global.setup.ts**: Creates ephemeral HA container (handled by hass-taste-test)
- **hass-taste-test**: Ephemeral HA instance management

## Verification Contract

**Project type**: greenfield (new test files only, no production code changes)

**Entry points**:
- `tests/e2e/trip-crud.spec.ts` - main test file
- `tests/e2e/pages/trips.page.ts` - Page Object for trips
- `tests/e2e/auth.setup.ts` - existing authentication setup (no changes)

**Observable signals**:
- PASS: Trip card appears in `.trips-list` with correct values, trip count changes
- FAIL: Form stays open, trip not visible, console errors, wrong data displayed

**Hard invariants**:
- Auth state must be valid - storageState from auth.setup.ts
- Vehicle "Coche2" must be configured
- Dialog must be accepted for delete to proceed

**Seed data**:
- Vehicle "Coche2" configured via Config Flow in auth.setup.ts
- Authenticated session via storageState

**Dependency map**:
- `tests/e2e/auth.setup.ts` - sets up Coche2 vehicle
- `tests/e2e/test-helpers.ts` - TripPanel base class

**Escalate if**:
- Config Flow fails during auth.setup.ts (integration not configured)
- Shadow DOM selectors fail to find elements (panel.js version mismatch)
- Dialog not triggered on delete click (frontend regression)
