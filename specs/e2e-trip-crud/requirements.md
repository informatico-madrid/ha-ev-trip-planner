# Requirements: E2E Trip CRUD Tests

## Goal
Create smoke tests for EV Trip Planner CRUD operations (Create, Edit, Delete) in GitHub Actions using Playwright. First E2E tests for the project.

## User Stories

### US-0: Infrastructure Setup
**As a** CI engineer
**I want to** have Playwright and Auth configured for CI
**So that** E2E tests can run in GitHub Actions

**Acceptance Criteria:**
- [ ] AC-0.1: `playwright.config.ts` exists with baseURL, timeout, retries configured for GitHub Actions
- [ ] AC-0.2: `auth.setup.ts` uses globalSetup to start ephemeral HA and write `server-info.json`
- [ ] AC-0.3: `globalTeardown.ts` stops ephemeral HA after test run

**Note:** FR-1 and FR-2 are cross-cutting infrastructure concerns that support all user stories below.

### US-1: Create Trip Smoke Test
**As a** Home Assistant user
**I want to** create a new trip from the UI
**So that** I can schedule a one-time trip

**Acceptance Criteria:**
- [ ] AC-1.1: Navigate to panel at `/ev-trip-planner-{vehicle_id}`
- [ ] AC-1.2: Click "+ Agregar Viaje" button
- [ ] AC-1.3: Select trip type "puntual" (one-time trip)
- [ ] AC-1.4: Fill form fields with test values:
  - Trip name: "Test Commute"
  - Day: Monday
  - Time: 08:00
  - km: 50
  - kwh: 15
- [ ] AC-1.5: Submit form via "Crear Viaje" button
- [ ] AC-1.6: Verify trip appears in trips list with submitted values
- [ ] AC-1.7: Clean up created trip after test (implicit - see FR-6 note)

### US-2: Edit Trip Smoke Test
**As a** Home Assistant user
**I want to** edit an existing trip
**So that** I can update trip details (time, km, description)

**Acceptance Criteria:**
- [ ] AC-2.1: Create a test trip first (recurrente type, day: Tuesday, time: 09:00, km: 30, kwh: 10)
- [ ] AC-2.2: Click edit button (pencil icon) on trip card
- [ ] AC-2.3: Modify km to 35 and description to "Updated Test Route"
- [ ] AC-2.4: Submit via "Guardar Cambios" button
- [ ] AC-2.5: Verify updated values display in trip card
- [ ] AC-2.6: Clean up test trip after test (implicit - see FR-6 note)

### US-3: Delete Trip Smoke Test
**As a** Home Assistant user
**I want to** delete an existing trip
**So that** I can remove outdated or incorrect trips

**Acceptance Criteria:**
- [ ] AC-3.1: Create a test trip first (puntual type, day: Wednesday, time: 10:00, km: 20, kwh: 5)
- [ ] AC-3.2: Click delete button (trash icon) on trip card
- [ ] AC-3.3: Confirm deletion in browser dialog
- [ ] AC-3.4: Verify trip no longer appears in trips list
- [ ] AC-3.5: Clean up any remaining data (implicit - see FR-6 note)

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Playwright config for CI | High | `playwright.config.ts` exists with baseURL, timeout, retries configured for GitHub Actions |
| FR-2 | Auth setup for HA in CI | High | `auth.setup.ts` uses globalSetup to start ephemeral HA and write `server-info.json` |
| FR-3 | Trip creation test | High | `create-trip.spec.ts` covers puntual trip creation |
| FR-4 | Trip edit test | Medium | `edit-trip.spec.ts` modifies km and validates update |
| FR-5 | Trip delete test | Medium | `delete-trip.spec.ts` confirms deletion removes trip from list |
| FR-6 | Test cleanup/isolation | High | **Implicit in all user stories.** Each test creates its own trip and deletes it; tests are independent. AC-1.7, AC-2.6, AC-3.5 reference cleanup but it is not a separate user story - it is a mandatory part of test hygiene for US-1, US-2, and US-3 respectively. |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | CI execution | Timeout | 60 min max (GitHub Actions job timeout) |
| NFR-2 | Test isolation | Environment | Docker HA container per test run |
| NFR-3 | Selector stability | Shadow DOM | Use web-first locators (getByRole, getByLabel, getByTestId) — `>>` pierce syntax is FORBIDDEN anti-pattern |
| NFR-4 | Browser | Engine | Chromium (Playwright default in CI) |
| NFR-5 | Parallel execution | Workers | 1 worker in CI (--workers=1) to avoid HA conflicts |

## Glossary

| Term | Definition |
|------|------------|
| **Shadow DOM** | Encapsulated DOM tree inside Lit web component; requires pierce selector (`>>`) for Playwright |
| **EV Trip Planner panel** | Lit web component at `/ev-trip-planner-{vehicle_id}` URL |
| **Recurrente trip** | Weekly recurring trip with day of week + time |
| **Puntual trip** | One-time trip with specific datetime |
| **globalSetup** | Playwright hook that runs once before all tests; used to start ephemeral HA |
| **globalTeardown** | Playwright hook that runs once after all tests; used to stop ephemeral HA |
| **Ephemeral HA** | Temporary Home Assistant instance started by globalSetup for isolated testing |
| **Pierce selector** | Playwright `>>` syntax — **FORBIDDEN** anti-pattern per homeassistant-selector-map skill; use web-first locators instead |
| **HA service** | Backend API called via `hass.callService('ev_trip_planner', service_name, data)` |

## Out of Scope

- Unit tests for trip_manager (already exist in `tests/test_trip_crud.py`)
- Integration tests with real EMHASS
- Visual regression testing
- Multi-vehicle scenarios
- Pause/resume trip functionality
- Performance/load testing
- Cross-browser testing (Firefox, WebKit)
- Testing in non-CI environment

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `playwright` in package.json | Already present | v1.58.2 |
| `auth.setup.ts` | Must create | globalSetup script to start ephemeral HA |
| `globalTeardown.ts` | Must create | Stop ephemeral HA after tests |
| `playwright.config.ts` | Must create | Configure for HA testing |
| `tests/e2e/` directory | Must create | Location for E2E test files |
| GitHub Actions workflow | Already exists | `.github/workflows/playwright.yml` |

## Success Criteria

1. All 3 smoke tests pass in GitHub Actions
2. Each test is fully isolated (creates and cleans up its own data)
3. No flaky selectors - tests use stable Shadow DOM pierce patterns
4. Tests complete within 60-minute GitHub Actions timeout
5. No manual intervention required - fully automated CI run

## Verification Contract

**Project type**: fullstack (HA integration with Lit web component frontend + Python backend)

**Entry points**:
- Panel URL: `/ev-trip-planner-{vehicle_id}` (via HA proxy)
- Service calls: `hass.callService('ev_trip_planner', 'trip_create'|'trip_update'|'delete_trip')`

**Observable signals**:
- PASS looks like:
  - Trip card appears in list after create with correct values
  - Trip card shows updated values after edit
  - Trip card disappears from list after delete
  - Browser dialogs (confirm) dismissed successfully
- FAIL looks like:
  - Form submission error alert shown
  - Trip does not appear in list
  - Trip still present after delete confirmation
  - 404 or timeout loading panel

**Hard invariants**:
- Auth session remains valid throughout test
- Vehicle_id matches the configured vehicle
- Test cleanup does not delete other users' trips
- HA services respond within timeout (30s)

**Seed data**:
- Valid HA user with access to `ev_trip_planner` domain
- At least one configured vehicle with `vehicle_id` matching panel URL
- No pre-existing trips required (tests create their own)

**Dependency map**:
- `custom_components/ev_trip_planner/frontend/panel.js` - Lit web component
- `custom_components/ev_trip_planner/trip_manager.py` - Backend CRUD logic
- `tests/test_trip_crud.py` - Unit tests (same logic, different layer)

**Escalate if**:
- Ephemeral HA fails to start in globalSetup
- Shadow DOM structure changes and pierce selectors break
- HA services return errors that prevent CRUD operations
- Test data persists after cleanup causing subsequent test failures

## Unresolved Questions

- How to handle the browser confirm dialog for delete (native `window.confirm` vs Playwright dialog handler)?
- Should tests run against real HA services or mocked responses?
- What `vehicle_id` should be used in CI - hardcoded or from config?

## Next Steps

1. Create `playwright.config.ts` in project root
2. Create `auth.setup.ts` globalSetup to start ephemeral HA
3. Create `globalTeardown.ts` to stop ephemeral HA
4. Create `tests/e2e/create-trip.spec.ts`
5. Create `tests/e2e/edit-trip.spec.ts`
6. Create `tests/e2e/delete-trip.spec.ts`
7. Verify tests pass in GitHub Actions
