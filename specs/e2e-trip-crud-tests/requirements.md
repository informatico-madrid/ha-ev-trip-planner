# Requirements: E2E Trip CRUD Tests

## Goal
Create browser-based E2E Playwright tests that verify CRUD functionality for trips in the EV Trip Planner panel. The existing `auth.setup.ts` provides authentication and Config Flow setup that tests reuse via `storageState`.

## User Stories

### US-1: Trip List Loading Test
**As a** test engineer
**I want** to verify trips load correctly from the trip_list service
**So that** I can confirm the panel displays existing trips properly

**Acceptance Criteria:**
- [ ] AC-1.1: Panel shows "No hay viajes" when no trips exist
- [ ] AC-1.2: Panel displays recurring trips with correct format (day, time)
- [ ] AC-1.3: Panel displays punctual trips with correct format (date, time)
- [ ] AC-1.4: Trip count badge updates when trips exist

### US-2: Create Trip Test
**As a** test engineer
**I want** to verify trip creation via the "+ Agregar Viaje" button
**So that** I can confirm trip_create service integration works

**Acceptance Criteria:**
- [ ] AC-2.1: Clicking "+ Agregar Viaje" opens trip form modal
- [ ] AC-2.2: Form shows "Recurrente" option with day selector
- [ ] AC-2.3: Form shows "Puntual" option without day selector
- [ ] AC-2.4: Selecting "Recurrente" reveals day selection UI
- [ ] AC-2.5: Selecting "Puntual" hides day selection UI
- [ ] AC-2.6: Filling form and clicking submit calls trip_create service
- [ ] AC-2.7: Form closes after successful creation
- [ ] AC-2.8: New trip appears in trip list immediately

### US-3: Edit Trip Test
**As a** test engineer
**I want** to verify trip editing via the "Editar" button
**So that** I can confirm trip_update service integration works

**Acceptance Criteria:**
- [ ] AC-3.1: Clicking "Editar" on a trip opens edit form
- [ ] AC-3.2: Form is pre-filled with existing trip data (type, day/time)
- [ ] AC-3.3: Modifying fields and submitting calls trip_update service
- [ ] AC-3.4: Updated trip displays new values in trip list

### US-4: Delete Trip Test
**As a** test engineer
**I want** to verify trip deletion via the "Eliminar" button
**So that** I can confirm delete_trip service integration works

**Acceptance Criteria:**
- [ ] AC-4.1: Clicking "Eliminar" shows confirmation dialog
- [ ] AC-4.2: Confirming deletion calls delete_trip service
- [ ] AC-4.3: Confirmed deletion removes trip from list
- [ ] AC-4.4: Canceling deletion keeps trip in list

### US-5: Pause/Resume Recurring Trip Test
**As a** test engineer
**I want** to verify pause/resume actions on recurring trips
**So that** I can confirm pause_recurring_trip and resume_recurring_trip services work

**Acceptance Criteria:**
- [ ] AC-5.1: Active recurring trip shows "Pausar" button
- [ ] AC-5.2: Clicking "Pausar" calls pause_recurring_trip service
- [ ] AC-5.3: Paused trip shows as inactive (visual indicator changes)
- [ ] AC-5.4: Paused trip shows "Reanudar" button
- [ ] AC-5.5: Clicking "Reanudar" calls resume_recurring_trip service
- [ ] AC-5.6: Resumed trip shows as active again

### US-6: Complete/Cancel Punctual Trip Test
**As a** test engineer
**I want** to verify complete/cancel actions on punctual trips
**So that** I can confirm complete_punctual_trip and cancel_punctual_trip services work

**Acceptance Criteria:**
- [ ] AC-6.1: Active punctual trip shows "Completar" button
- [ ] AC-6.2: Clicking "Completar" calls complete_punctual_trip service
- [ ] AC-6.3: Completed trip is removed from active list
- [ ] AC-6.4: Active punctual trip shows "Cancelar" button
- [ ] AC-6.5: Clicking "Cancelar" calls cancel_punctual_trip service
- [ ] AC-6.6: Cancelled trip is removed from active list

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Navigate to EV Trip Planner panel via sidebar | High | Click EV Trip Planner in sidebar, panel loads |
| FR-2 | Display "No hay viajes" when no trips exist | High | Empty state message visible |
| FR-3 | Display existing trips with correct format | High | Recurring shows day/time, punctual shows date/time |
| FR-4 | Open create trip modal via "+ Agregar Viaje" button | High | Modal appears with form fields |
| FR-5 | Recurring/Puntual type toggle shows/hides day selector | High | Day selector visible only for Recurrente |
| FR-6 | Submit trip form calls trip_create service | High | Service called with form data, trip created |
| FR-7 | Open edit form via "Editar" button with pre-filled data | High | Form opens with existing trip values |
| FR-8 | Submit edit form calls trip_update service | High | Service called with updated data |
| FR-9 | "Eliminar" shows confirmation dialog | High | Dialog with Confirm/Cancel options |
| FR-10 | Confirm delete calls delete_trip service | High | Service called, trip removed |
| FR-11 | Cancel delete keeps trip in list | High | Dialog closes, trip unchanged |
| FR-12 | "Pausar" calls pause_recurring_trip service | High | Service called, trip shows inactive |
| FR-13 | "Reanudar" calls resume_recurring_trip service | High | Service called, trip shows active |
| FR-14 | "Completar" calls complete_punctual_trip service | High | Service called, trip removed from list |
| FR-15 | "Cancelar" calls cancel_punctual_trip service | High | Service called, trip removed from list |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test execution time | Total test suite | < 5 minutes |
| NFR-2 | Test reliability | Pass rate | 100% (no flaky tests) |
| NFR-3 | Browser support | Browsers | Chrome (primary), Firefox (verify) |
| NFR-4 | Selector robustness | Shadow DOM traversal | All locators use web-first APIs |
| NFR-5 | Test isolation | State between tests | Each test cleans up created data |

## Glossary

- **Shadow DOM**: Web Components encapsulation - elements inside `shadow-root` require web-first locators (`getByRole`, `getByText`, `getByLabel`) instead of CSS/XPath
- **storageState**: Playwright mechanism to persist authenticated session - tests reuse login state without re-authenticating
- **Config Flow**: Home Assistant UI flow for configuring integrations (vehicle name, sensors, etc.)
- **web-first locators**: Playwright locators that auto-wait and traverse Shadow DOM (`getByRole`, `getByText`, `getByLabel`)
- **Recurring trip**: Trip that repeats on specified days (e.g., every Monday at 8:00)
- **Punctual trip**: One-time trip on a specific date and time
- **trip_create/trip_update/delete_trip**: Home Assistant service calls for trip management
- **pause_recurring_trip/resume_recurring_trip**: Services to pause/resume recurring trips
- **complete_punctual_trip/cancel_punctual_trip**: Services to complete/cancel punctual trips

## Out of Scope

- Panel loading tests (URL validation, vehicle ID extraction) - covered by 021 spec
- Backend EV Trip Planner integration logic
- Home Assistant core functionality
- Performance testing beyond basic execution time
- Load testing
- Static code analysis / unit tests
- Firefox/Safari browser compatibility (Chrome primary only)

## Dependencies

- Home Assistant instance running with EV Trip Planner integration installed
- Vehicle "Coche2" configured with sensors via Config Flow
- `auth.setup.ts` completing successfully and saving `storageState` to `playwright/.auth/user.json`
- `playwright/.auth/panel-url.txt` containing panel URL (e.g., `http://localhost:8123/ev-trip-planner-Coche2`)
- Server info at `playwright/.auth/server-info.json`
- Playwright test runner with `@playwright/test` framework

## Success Criteria

- [ ] All 6 user stories implemented as Playwright E2E tests
- [ ] Tests use `storageState` from `auth.setup.ts` (no login code in tests)
- [ ] All locators use web-first APIs (getByRole, getByText, getByLabel)
- [ ] No `waitForTimeout` calls - all waits use `expect()` with auto-waiting
- [ ] Tests navigate via sidebar, not hardcoded URLs
- [ ] Tests pass in Chrome with 100% reliability
- [ ] Tests run in < 5 minutes total
- [ ] Created trips are cleaned up after each test

## Verification Contract

**Project type**: `fullstack` (HA frontend + HTTP API services)

**Entry points**:
- `GET /ev-trip-planner-{vehicle_id}` - EV Trip Planner panel
- `POST` services: `trip_create`, `trip_update`, `delete_trip`, `pause_recurring_trip`, `resume_recurring_trip`, `complete_punctual_trip`, `cancel_punctual_trip`
- UI buttons: "+ Agregar Viaje", "Editar", "Eliminar", "Pausar", "Reanudar", "Completar", "Cancelar"

**Observable signals**:
- PASS looks like: Trip appears/disappears from list, form modal opens/closes, button state changes (Pausar -> Reanudar), confirmation dialog appears
- FAIL looks like: Service call error toast, form validation error, trip not appearing in list after create, element not found timeout

**Hard invariants**:
- Authentication state must remain valid (storageState reused from auth.setup.ts)
- Tests must not modify auth.setup.ts or authentication flow
- Other users' data must not be affected (isolated to configured vehicle "Coche2")

**Seed data**:
- Vehicle "Coche2" configured via Config Flow
- At least one recurring trip and one punctual trip pre-created for edit/delete/pause tests, OR tests create them first

**Dependency map**:
- `auth.setup.ts` - provides authenticated session and panel URL
- Trip panel frontend - renders trip list and forms
- Home Assistant trip services - backend service calls

**Escalate if**:
- Shadow DOM structure changes and web-first locators break
- Service names change (trip_create, etc.)
- Button labels change ("Pausar", "Reanudar", etc.)
- Config Flow vehicle name changes from "Coche2"

## Unresolved Questions

- Should tests create trips as setup (before each test) or reuse existing trips?
- Is trip data cleanup required between tests, or does each test create isolated data?
- Should parameterized vehicle names be supported for multi-vehicle testing?

## Next Steps

1. Review requirements with stakeholders for approval
2. Create technical design document with page object structure
3. Implement tests following the design
4. Verify tests pass in Chrome
