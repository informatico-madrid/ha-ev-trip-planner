# Requirements: E2E Test Suite for EV Trip Planner

## Goal

Create an end-to-end Playwright test suite that verifies the EV Trip Planner integration: install via Config Flow, open the vehicle panel, create a trip, and verify the trip appears in the listing.

## User Stories

### US-1: Install EV Trip Planner via Config Flow
**As a** Playwright test
**I want to** run the Config Flow UI to install the EV Trip Planner integration
**So that** the integration is available in Home Assistant for testing

**Acceptance Criteria:**
- [ ] AC-1.1: Navigate to HA integrations page
- [ ] AC-1.2: Click "Add Integration" and select "EV Trip Planner"
- [ ] AC-1.3: Fill in required Config Flow fields (vehicle name)
- [ ] AC-1.4: Complete Config Flow successfully
- [ ] AC-1.5: EV Trip Planner panel appears in HA sidebar
- [ ] AC-1.6: auth.setup.ts saves storageState after successful Config Flow

### US-2: View Vehicle Panel
**As a** Playwright test
**I want to** navigate to the EV Trip Planner vehicle panel
**So that** I can interact with the panel to create trips

**Acceptance Criteria:**
- [ ] AC-2.1: Click EV Trip Planner sidebar link (not direct URL)
- [ ] AC-2.2: Panel loads at `/ev-trip-planner-{vehicle_id}`
- [ ] AC-2.3: Panel renders without console errors
- [ ] AC-2.4: Shadow DOM content is accessible via pierce combinator (`>>`)

### US-3: Create a Trip
**As a** Playwright test
**I want to** fill in the trip form and submit it
**So that** a new trip is created in the EV Trip Planner

**Acceptance Criteria:**
- [ ] AC-3.1: Click `.add-trip-btn` (inside Shadow DOM)
- [ ] AC-3.2: Trip form overlay `.trip-form-overlay` appears
- [ ] AC-3.3: Fill `#trip-name` field with trip name
- [ ] AC-3.4: Fill `#trip-type` field (dropdown/selector)
- [ ] AC-3.5: Fill `#trip-time` field (datetime picker)
- [ ] AC-3.6: Submit form successfully
- [ ] AC-3.7: Form overlay closes and trip appears in list

### US-4: Verify Trip Appears in Vehicle Panel
**As a** Playwright test
**I want to** verify the created trip is visible in the trips list
**So that** I confirm the create operation persisted correctly

**Acceptance Criteria:**
- [ ] AC-4.1: Trip card with `data-trip-id` attribute exists in `.trips-list`
- [ ] AC-4.2: Trip name displayed matches the created trip
- [ ] AC-4.3: Trip type displayed matches the selected type
- [ ] AC-4.4: Trip time displayed matches the entered time

### US-5: Clean Up Test Data After Each Test
**As a** Playwright test
**I want to** delete created vehicles and trips after each test
**So that** tests do not pollute each other

**Acceptance Criteria:**
- [ ] AC-5.1: afterEach hook runs after every test
- [ ] AC-5.2: Created trips are deleted via API or UI
- [ ] AC-5.3: Created vehicles are deleted via Config Flow "Remove" option
- [ ] AC-5.4: No residual data remains for subsequent tests

### US-6: Run E2E Tests in CI (GitHub Actions)
**As a** CI pipeline
**I want to** execute Playwright tests on every PR
**So that** regressions are caught before merging

**Acceptance Criteria:**
- [ ] AC-6.1: `.github/workflows/playwright.yml` triggers on PR
- [ ] AC-6.2: Workflow installs dependencies with `npm ci`
- [ ] AC-6.3: Workflow runs `npx playwright test tests/e2e/`
- [ ] AC-6.4: Workflow uploads test artifacts (screenshots/video) on failure
- [ ] AC-6.5: Tests run in Chromium only (no Firefox/WebKit)

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | playwright.config.ts | High | Must reference global.setup.ts and global.teardown.ts; use Chromium only |
| FR-2 | auth.setup.ts | High | Must run Config Flow UI and save storageState to auth.json |
| FR-3 | ConfigFlowPage POM | High | Page class with methods for adding integration, filling fields, completing flow |
| FR-4 | EVTripPlannerPage POM | High | Page class with methods for opening panel, adding trip, verifying trips |
| FR-5 | Shadow DOM selectors | High | All internal selectors use pierce combinator `>>` (e.g., `ev-trip-planner-panel >> .add-trip-btn`) |
| FR-6 | vehicle.spec.ts | High | Test creates vehicle via Config Flow and verifies panel opens |
| FR-7 | trip.spec.ts | High | Test creates trip and verifies it appears in vehicle panel |
| FR-8 | Test cleanup | High | Each spec file uses afterEach to delete created data |
| FR-9 | CI workflow | High | Existing `.github/workflows/playwright.yml` runs tests on PR |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Performance | Total test runtime | < 5 minutes for full suite |
| NFR-2 | Browser | Browser choice | Chromium only (no Firefox/WebKit) |
| NFR-3 | Isolation | Shared state between tests | Zero shared state; each test creates and tears down its own data |

## Glossary

- **ephemeral HA**: Temporary Home Assistant instance created by hass-taste-test in a temp directory, used for testing
- **Shadow DOM**: Encapsulated DOM tree within a web component; requires pierce combinator (`>>`) to select elements inside
- **pierce combinator**: Playwright selector syntax (`>>`) that traverses into Shadow DOM roots
- **POM**: Page Object Model — pattern where each page/screen has a corresponding class with methods
- **hass-taste-test**: npm package that creates ephemeral Home Assistant instances for E2E testing
- **storageState**: Playwright file containing browser context cookies and localStorage; used to persist authenticated sessions
- **Config Flow**: Home Assistant's step-by-step UI wizard for adding integrations
- **panel_custom**: Home Assistant API for registering native panel iframes (different from Lovelace cards)

## Out of Scope

- Error flows (invalid input, network failures, Config Flow rejection)
- Multi-vehicle scenarios (2+ vehicles in same test)
- Firefox or WebKit browser testing
- Manual testing
- Visual regression testing
- Performance benchmarking

## Dependencies

- `@playwright/test@^1.58.2` — already in package.json
- `hass-taste-test@^0.2.7` — already in package.json
- `tests/global.setup.ts` — already exists; starts ephemeral HA, copies panel.js, saves server-info.json
- `tests/global.teardown.ts` — already exists; cleans up ephemeral HA
- `.github/workflows/playwright.yml` — already exists; runs `npx playwright test tests/e2e/`

## Success Criteria

- [ ] `playwright.config.ts` created with globalSetup/globalTeardown pointing to existing global.setup.ts/global.teardown.ts
- [ ] `tests/e2e/auth.setup.ts` created and runs Config Flow, saves storageState
- [ ] `tests/e2e/pages/ConfigFlowPage.ts` created with Config Flow POM methods
- [ ] `tests/e2e/pages/EVTripPlannerPage.ts` created with panel POM methods
- [ ] `tests/e2e/vehicle.spec.ts` creates vehicle and verifies panel opens
- [ ] `tests/e2e/trip.spec.ts` creates trip and verifies listing
- [ ] All tests use Shadow DOM pierce combinator (`>>`) for internal selectors
- [ ] All tests clean up created data in afterEach
- [ ] GitHub Actions workflow runs on PR and passes

## Verification Contract

**Project type**: fullstack (HA backend + browser UI)

**Entry points**:
- `POST /api/config/config_entries/entry/{entry_id}/remove` — remove integration
- `DELETE /api/states/{entity_id}` — delete trip entities
- UI: Config Flow wizard at `/config/integrations`
- UI: EV Trip Planner panel at `/ev-trip-planner-{vehicle_id}`

**Observable signals**:
- PASS: Config Flow completes, sidebar shows EV Trip Planner, trip card with data-trip-id appears in list
- FAIL: Console errors on panel load, Config Flow fields not found, trip not persisted after creation

**Hard invariants**:
- Auth: ephemeral HA must stay authenticated (storageState valid throughout test file)
- Permissions: integration can only access its own entities
- Adjacent flows: removing integration does not affect other HA integrations

**Seed data**:
- Ephemeral HA with dev/dev user (created by hass-taste-test)
- EV Trip Planner panel.js copied to www/ (done by global.setup.ts)

**Dependency map**:
- `global.setup.ts` / `global.teardown.ts` — shared ephemeral HA lifecycle
- `auth.setup.ts` — shared auth storageState

**Escalate if**:
- Config Flow UI structure changes (selectors break)
- Shadow DOM structure of EVTripPlannerPanel changes
- hass-taste-test API changes

## Unresolved Questions

- What are the exact field names in the EV Trip Planner Config Flow? (Need to verify against `strings.json` and `config_flow.py`)
- Does HA require a page reload after Config Flow before the panel appears in the sidebar?
- What entity selector is required for presence detection in ephemeral HA?

## Next Steps

1. Verify Config Flow field names by inspecting `config_flow.py` and `strings.json`
2. Create `playwright.config.ts` with globalSetup/globalTeardown references
3. Create `tests/e2e/auth.setup.ts` to automate Config Flow
4. Create `tests/e2e/pages/ConfigFlowPage.ts` POM
5. Create `tests/e2e/pages/EVTripPlannerPage.ts` POM
6. Create `tests/e2e/vehicle.spec.ts` with US-1 and US-2
7. Create `tests/e2e/trip.spec.ts` with US-3 and US-4
8. Run test suite locally and iterate on selectors
