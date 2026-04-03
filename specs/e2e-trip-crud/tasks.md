# Tasks: E2E Trip CRUD Tests

Feature ID: e2e-trip-crud
Total Tasks: 52
Constitution: POC-first workflow (GREENFIELD)

## Phase 1: Infrastructure + POC (24 tasks)

### Setup

- [x] T001 [US-0] Create tests/e2e directory structure
  - **Do**:
    1. Create `tests/e2e/` directory
    2. Add .gitkeep placeholder
  - **Files**: `tests/e2e/.gitkeep`
  - **Done when**: Directory exists
  - **Verify**: `test -d tests/e2e && echo "OK"`
  - **Commit**: `feat(e2e): create tests/e2e directory`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for test directory structure
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for test file organization

### Playwright Configuration

- [x] T002 [P] [US-0] Create playwright.config.ts with CI configuration
  - **Do**:
    1. Create `playwright.config.ts` with baseURL=http://localhost:8123
    2. Configure timeout=30000, retries=1, workers=1
    3. Set testDir='./tests/e2e'
    4. Configure reporter: list + html
    5. Set globalSetup='./auth.setup.ts', globalTeardown='./globalTeardown.ts'
    6. Enable trace='on-first-retry', screenshot='only-on-failure', video='retain-on-failure'
  - **Files**: `playwright.config.ts`
  - **Done when**: playwright.config.ts exists with valid config
  - **Verify**: `cat playwright.config.ts | grep -q "defineConfig" && echo "OK"`
  - **Commit**: `feat(e2e): add playwright.config.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for Playwright configuration patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for CI configuration

- [x] T003 [P] [US-0] Create globalTeardown.ts skeleton
  - **Do**:
    1. Create `globalTeardown.ts` with globalTeardown export
    2. Add cleanup logic for state files (server-info.json)
    3. Add descriptive logging
  - **Files**: `globalTeardown.ts`
  - **Done when**: globalTeardown.ts exists
  - **Verify**: `cat globalTeardown.ts | grep -q "globalTeardown" && echo "OK"`
  - **Commit**: `feat(e2e): add globalTeardown.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for global teardown patterns

- [x] T004 [P] [US-0] Create playwright/.auth directory
  - **Do**:
    1. Create `playwright/.auth/` directory
    2. Add .gitkeep placeholder
  - **Files**: `playwright/.auth/.gitkeep`
  - **Done when**: Directory exists
  - **Verify**: `test -d playwright/.auth && echo "OK"`
  - **Commit**: `feat(e2e): create playwright auth directory`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for auth state storage

### Auth Setup - HA Wait

- [x] T005 [P] [US-0] Create auth.setup.ts with HA wait function
  - **Do**:
    1. Create `auth.setup.ts` with globalSetup export
    2. Implement waitForHA() to poll http://localhost:8123 until HTTP 200
    3. Add timeout handling (120s for HA startup)
    4. Add error logging for HA connection failures
  - **Files**: `auth.setup.ts`
  - **Done when**: auth.setup.ts has waitForHA function
  - **Verify**: `cat auth.setup.ts | grep -q "waitForHA" && echo "OK"`
  - **Commit**: `feat(e2e): add auth.setup.ts with HA wait`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for global setup patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA startup patterns

- [x] T006 [P] [US-0] Implement trusted_networks bypass in auth.setup.ts
  - **Do**:
    1. Add page.goto('/') navigation (only allowed entry point per HA SPA pattern)
    2. Add waitForURL('/home') after trusted_networks bypass
    3. Verify no login form appears (trusted_networks bypass works)
    4. Save storageState to 'playwright/.auth/user.json' after navigation
  - **Files**: `auth.setup.ts`
  - **Done when**: Auth flow navigates to /home without login, storageState saved
  - **Verify**: `cat auth.setup.ts | grep -q "storageState" && echo "OK"`
  - **Commit**: `feat(e2e): implement trusted_networks bypass in auth.setup`
  - **Skills**:
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for SPA navigation rules and trusted_networks auth

### Auth Setup - Config Flow Steps

- [x] T007 [P] [US-0] Navigate to integrations page via sidebar
  - **Do**:
    1. Click sidebar link to integrations page
    2. Use web-first locator: getByRole('link', { name: 'Integrations' })
    3. Wait for /config/integrations URL
  - **Files**: `auth.setup.ts`
  - **Done when**: Successfully navigated to integrations page
  - **Verify**: `cat auth.setup.ts | grep -q "getByRole.*link.*Integrations" && echo "OK"`
  - **Commit**: `feat(e2e): navigate to integrations page via sidebar`
  - **Skills**:
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for sidebar navigation

- [x] T008 [P] [US-0] Click Add Integration button
  - **Do**:
    1. Click "+ Add Integration" button
    2. Use web-first locator: getByRole('button', { name: /Add Integration/i })
    3. Wait for integration search dialog to appear
  - **Files**: `auth.setup.ts`
  - **Done when**: Add Integration dialog opens
  - **Verify**: `cat auth.setup.ts | grep -q "Add Integration" && echo "OK"`
  - **Commit**: `feat(e2e): click Add Integration button`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for button interaction patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA UI selectors

- [x] T009 [P] [US-0] Search for EV Trip Planner integration
  - **Do**:
    1. Find integration search textbox
    2. Use web-first locator: getByRole('textbox', { name: /search/i })
    3. Type "EV Trip Planner"
    4. Wait for search results
  - **Files**: `auth.setup.ts`
  - **Done when**: Search textbox found and EV Trip Planner appears
  - **Verify**: `cat auth.setup.ts | grep -q "EV Trip Planner" && echo "OK"`
  - **Commit**: `feat(e2e): search for EV Trip Planner integration`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for text input patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA form selectors

- [x] T010 [P] [US-0] Config Flow Step 1: vehicle_name field
  - **Do**:
    1. Click on EV Trip Planner integration result
    2. Wait for Step 1 form (async_step_user)
    3. Fill vehicle_name field: getByRole('textbox', { name: /vehicle_name/i })
    4. Fill value: "test_vehicle"
    5. Submit via Next/Submit button
  - **Files**: `auth.setup.ts`
  - **Done when**: Step 1 submitted with vehicle_name=test_vehicle
  - **Verify**: `cat auth.setup.ts | grep -q "test_vehicle" && echo "OK"`
  - **Commit**: `feat(e2e): complete Config Flow Step 1 - vehicle_name`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for form field patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA Config Flow selectors

- [x] T011 [P] [US-0] Config Flow Step 2: sensors fields
  - **Do**:
    1. Wait for Step 2 form (async_step_sensors)
    2. Fill battery_capacity_kwh: "60"
    3. Fill charging_power_kw: "11"
    4. Fill kwh_per_km: "0.17"
    5. Fill safety_margin_percent: "20"
    6. Submit via Next/Submit button
  - **Files**: `auth.setup.ts`
  - **Done when**: Step 2 submitted with sensor values
  - **Verify**: `cat auth.setup.ts | grep -q "battery_capacity_kwh" && echo "OK"`
  - **Commit**: `feat(e2e): complete Config Flow Step 2 - sensors`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for form filling patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA Config Flow field selectors

- [ ] T012 [P] [US-0] Config Flow Step 3: emhass fields
  - **Do**:
    1. Wait for Step 3 form (async_step_emhass)
    2. Accept defaults: planning_horizon_days=7, max_deferrable_loads=50, index_cooldown_hours=24
    3. Leave planning_sensor empty (optional)
    4. Submit via Next/Submit button
  - **Files**: `auth.setup.ts`
  - **Done when**: Step 3 submitted with defaults
  - **Verify**: `cat auth.setup.ts | grep -q "planning_horizon" && echo "OK"`
  - **Commit**: `feat(e2e): complete Config Flow Step 3 - emhass`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for accepting default values
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA Config Flow selectors

- [ ] T013 [P] [US-0] Config Flow Step 4: presence fields
  - **Do**:
    1. Wait for Step 4 form (async_step_presence)
    2. Wait for entity selector to appear (charging_sensor)
    3. If selector appears with entities, click to select one
    4. If no entities available, proceed without selection (server-side auto-select)
    5. Submit via Next/Finish button
  - **Files**: `auth.setup.ts`
  - **Done when**: Step 4 submitted, integration installed
  - **Verify**: `cat auth.setup.ts | grep -q "charging_sensor" && echo "OK"`
  - **Commit**: `feat(e2e): complete Config Flow Step 4 - presence`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for entity selector patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA entity selector handling

- [ ] T014 [P] [US-0] Config Flow Step 5: notifications fields
  - **Do**:
    1. Wait for Step 5 form (async_step_notifications)
    2. Leave notification_service empty (optional)
    3. Leave notification_devices empty (optional)
    4. Submit via Finish button
  - **Files**: `auth.setup.ts`
  - **Done when**: Step 5 submitted, Config Flow complete
  - **Verify**: `cat auth.setup.ts | grep -q "notification" && echo "OK"`
  - **Commit**: `feat(e2e): complete Config Flow Step 5 - notifications`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for optional form fields
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for HA Config Flow submit patterns

### Trip Helpers

- [ ] T015 [P] [US-1] Create trips-helpers.ts with navigateToPanel function
  - **Do**:
    1. Create `tests/e2e/trips-helpers.ts`
    2. Add navigateToPanel(page) using page.goto('/') then waitForURL('/home')
    3. Click sidebar link: getByRole('link', { name: 'EV Trip Planner' })
    4. Wait for URL pattern: /\/ev_trip_planner\//
    5. Return the page for chaining
  - **Files**: `tests/e2e/trips-helpers.ts`
  - **Done when**: navigateToPanel helper exists
  - **Verify**: `cat tests/e2e/trips-helpers.ts | grep -q "navigateToPanel" && echo "OK"`
  - **Commit**: `feat(e2e): add navigateToPanel helper`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for navigation patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for SPA navigation with sidebar

- [ ] T016 [P] [US-1] Create trips-helpers.ts with createTestTrip function
  - **Do**:
    1. Add createTestTrip(page, tripType, datetime, km, kwh, description) function
    2. Click "+ Agregar Viaje" button with getByRole
    3. Select trip type (puntual/recurrente) with getByRole('combobox')
    4. Fill form fields using web-first locators
    5. Submit via "Crear Viaje" button
    6. Return trip identifier for cleanup
  - **Files**: `tests/e2e/trips-helpers.ts`
  - **Done when**: createTestTrip helper exists
  - **Verify**: `cat tests/e2e/trips-helpers.ts | grep -q "createTestTrip" && echo "OK"`
  - **Commit**: `feat(e2e): add createTestTrip helper`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for form interaction patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for test data fixtures

- [ ] T017 [P] [US-1] Create trips-helpers.ts with deleteTestTrip function
  - **Do**:
    1. Add deleteTestTrip(page, tripId) function
    2. Find trip by ID in the list
    3. Click delete button (trash icon)
    4. Handle browser dialog with page.on('dialog')
    5. Verify trip is removed from list
  - **Files**: `tests/e2e/trips-helpers.ts`
  - **Done when**: deleteTestTrip helper exists
  - **Verify**: `cat tests/e2e/trips-helpers.ts | grep -q "deleteTestTrip" && echo "OK"`
  - **Commit**: `feat(e2e): add deleteTestTrip helper`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for dialog handling patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for cleanup patterns

### Create Trip Test

- [ ] T018 [P] [US-1] Create create-trip.spec.ts with test skeleton
  - **Do**:
    1. Create `tests/e2e/create-trip.spec.ts`
    2. Import from @playwright/test
    3. Import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers'
    4. Create test.describe with 'Create Trip' title
    5. Add test with descriptive name
  - **Files**: `tests/e2e/create-trip.spec.ts`
  - **Done when**: create-trip.spec.ts has test skeleton
  - **Verify**: `cat tests/e2e/create-trip.spec.ts | grep -q "test" && echo "OK"`
  - **Commit**: `feat(e2e): add create-trip.spec.ts skeleton`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for test file structure
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for E2E test structure

- [ ] T019 [P] [US-1] Implement create-trip.spec.ts navigation flow
  - **Do**:
    1. Implement page.goto('/') in test
    2. Implement page.waitForURL('/home')
    3. Implement sidebar navigation to EV Trip Planner panel
    4. Implement page.waitForURL(/\/ev_trip_planner\/)
  - **Files**: `tests/e2e/create-trip.spec.ts`
  - **Done when**: Test has complete navigation flow
  - **Verify**: `cat tests/e2e/create-trip.spec.ts | grep -q "waitForURL" && echo "OK"`
  - **Commit**: `feat(e2e): implement navigation flow in create-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for navigation implementation
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for sidebar navigation

- [ ] T020 [P] [US-1] Implement create-trip.spec.ts form interaction
  - **Do**:
    1. Click "+ Agregar Viaje" button with getByRole
    2. Select trip type "puntual" with getByRole('combobox')
    3. Fill datetime-local: 2026-04-15T08:30
    4. Fill km: 50, kwh: 15
    5. Fill description: "Test Commute"
    6. Click "Crear Viaje" button to submit
  - **Files**: `tests/e2e/create-trip.spec.ts`
  - **Done when**: Test fills and submits trip form
  - **Verify**: `cat tests/e2e/create-trip.spec.ts | grep -q "fill\|click" && echo "OK"`
  - **Commit**: `feat(e2e): implement form interaction in create-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for form interaction patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for form field selectors

- [ ] T021 [P] [US-1] Implement create-trip.spec.ts assertions and cleanup
  - **Do**:
    1. Assert trip appears in trips list after creation
    2. Assert trip values match: km=50, kwh=15, description="Test Commute"
    3. Use expect with web-first locators
    4. Clean up: delete the created trip after test
  - **Files**: `tests/e2e/create-trip.spec.ts`
  - **Done when**: Test has assertions and cleanup
  - **Verify**: `cat tests/e2e/create-trip.spec.ts | grep -q "expect\|deleteTestTrip" && echo "OK"`
  - **Commit**: `feat(e2e): implement assertions in create-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for assertion patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for E2E assertions

- [ ] T022 [P] [US-1] Add TypeScript types to trips-helpers.ts
  - **Do**:
    1. Add TripData interface definition
    2. Add TripType enum or type
    3. Add explicit return types to all helper functions
    4. Add Page type annotations
  - **Files**: `tests/e2e/trips-helpers.ts`
  - **Done when**: Helper file has complete TypeScript types
  - **Verify**: `npx tsc --noEmit tests/e2e/trips-helpers.ts 2>&1 | head -5`
  - **Commit**: `feat(e2e): add TypeScript types to trips-helpers.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for TypeScript integration

### Phase 1 Quality Checkpoint

- [ ] T023 [VERIFY] Phase 1 Quality checkpoint: TypeScript compilation
  - **Do**: Run TypeScript compilation check on all created files
  - **Verify**: `npx tsc --noEmit playwright.config.ts auth.setup.ts globalTeardown.ts tests/e2e/*.ts 2>&1 | head -20`
  - **Done when**: All TypeScript files compile without errors
  - **Commit**: `chore(e2e): pass Phase 1 quality checkpoint`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for type checking

## Phase 2: Refactor + Remaining Tests (14 tasks)

### Edit Trip Test

- [ ] T024 [P] [US-2] Create edit-trip.spec.ts with test skeleton
  - **Do**:
    1. Create `tests/e2e/edit-trip.spec.ts`
    2. Import from @playwright/test
    3. Import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers'
    4. Create test.describe with 'Edit Trip' title
    5. Add test with descriptive name
  - **Files**: `tests/e2e/edit-trip.spec.ts`
  - **Done when**: edit-trip.spec.ts has test skeleton
  - **Verify**: `cat tests/e2e/edit-trip.spec.ts | grep -q "test" && echo "OK"`
  - **Commit**: `feat(e2e): add edit-trip.spec.ts skeleton`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for test file structure
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for E2E test structure

- [ ] T025 [P] [US-2] Implement edit-trip.spec.ts navigation and setup
  - **Do**:
    1. Implement page.goto('/') then waitForURL('/home')
    2. Navigate to EV Trip Planner panel via sidebar
    3. Create a recurrente trip first (day: Tuesday, time: 09:00, km: 30, kwh: 10)
  - **Files**: `tests/e2e/edit-trip.spec.ts`
  - **Done when**: Test creates setup trip for edit
  - **Verify**: `cat tests/e2e/edit-trip.spec.ts | grep -q "createTestTrip\|recurrente" && echo "OK"`
  - **Commit**: `feat(e2e): implement edit-trip.spec.ts setup`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for setup patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for test data setup

- [ ] T026 [P] [US-2] Implement edit-trip.spec.ts edit flow
  - **Do**:
    1. Click edit button (pencil icon) on trip card
    2. Use getByRole('button', { name: /edit/i })
    3. Wait for edit form to appear
    4. Modify km to 35
    5. Modify description to "Updated Test Route"
    6. Click "Guardar Cambios" button to submit
  - **Files**: `tests/e2e/edit-trip.spec.ts`
  - **Done when**: Test can edit a trip
  - **Verify**: `cat tests/e2e/edit-trip.spec.ts | grep -q "Guardar Cambios" && echo "OK"`
  - **Commit**: `feat(e2e): implement edit flow in edit-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for button interaction patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for edit button selectors

- [ ] T027 [P] [US-2] Implement edit-trip.spec.ts assertions and cleanup
  - **Do**:
    1. Assert trip card shows updated km=35 after save
    2. Assert trip card shows updated description="Updated Test Route"
    3. Clean up: delete the test trip after test
  - **Files**: `tests/e2e/edit-trip.spec.ts`
  - **Done when**: Test has assertions and cleanup
  - **Verify**: `cat tests/e2e/edit-trip.spec.ts | grep -q "expect\|deleteTestTrip" && echo "OK"`
  - **Commit**: `feat(e2e): implement assertions in edit-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for assertion patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for cleanup patterns

### Delete Trip Test

- [ ] T028 [P] [US-3] Create delete-trip.spec.ts with test skeleton
  - **Do**:
    1. Create `tests/e2e/delete-trip.spec.ts`
    2. Import from @playwright/test
    3. Import { createTestTrip, navigateToPanel, deleteTestTrip } from './trips-helpers'
    4. Create test.describe with 'Delete Trip' title
    5. Add test with descriptive name
  - **Files**: `tests/e2e/delete-trip.spec.ts`
  - **Done when**: delete-trip.spec.ts has test skeleton
  - **Verify**: `cat tests/e2e/delete-trip.spec.ts | grep -q "test" && echo "OK"`
  - **Commit**: `feat(e2e): add delete-trip.spec.ts skeleton`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for test file structure
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for E2E test structure

- [ ] T029 [P] [US-3] Implement delete-trip.spec.ts navigation and setup
  - **Do**:
    1. Implement page.goto('/') then waitForURL('/home')
    2. Navigate to EV Trip Planner panel via sidebar
    3. Create a puntual trip first (day: Wednesday, time: 10:00, km: 20, kwh: 5)
  - **Files**: `tests/e2e/delete-trip.spec.ts`
  - **Done when**: Test creates setup trip for delete
  - **Verify**: `cat tests/e2e/delete-trip.spec.ts | grep -q "createTestTrip\|puntual" && echo "OK"`
  - **Commit**: `feat(e2e): implement delete-trip.spec.ts setup`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for setup patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for test data setup

- [ ] T030 [P] [US-3] Implement delete-trip.spec.ts delete flow with dialog
  - **Do**:
    1. Set up dialog handler before clicking delete: page.on('dialog', async dialog => ...)
    2. Assert dialog message contains "¿Estás seguro de que quieres eliminar este viaje?"
    3. Accept dialog with dialog.accept()
    4. Click delete button (trash icon) with getByRole('button', { name: /delete/i })
  - **Files**: `tests/e2e/delete-trip.spec.ts`
  - **Done when**: Test handles delete dialog correctly
  - **Verify**: `cat tests/e2e/delete-trip.spec.ts | grep -q "dialog\|delete" && echo "OK"`
  - **Commit**: `feat(e2e): implement delete dialog handling in delete-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for dialog handling patterns
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for delete button selectors

- [ ] T031 [P] [US-3] Implement delete-trip.spec.ts assertions
  - **Do**:
    1. Assert trip no longer appears in trips list after deletion
    2. Use expect(tripCard).toBeHidden() or toHaveCount(0) for list verification
  - **Files**: `tests/e2e/delete-trip.spec.ts`
  - **Done when**: Test has delete assertions
  - **Verify**: `cat tests/e2e/delete-trip.spec.ts | grep -q "expect\|toBeHidden" && echo "OK"`
  - **Commit**: `feat(e2e): implement assertions in delete-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for assertion patterns
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for E2E assertions

### TypeScript Type Checking

- [ ] T032 [P] [US-1] Add TypeScript types to create-trip.spec.ts
  - **Do**:
    1. Add explicit Page type import
    2. Add type annotations to test function parameters
    3. Add interface for TripData
  - **Files**: `tests/e2e/create-trip.spec.ts`
  - **Done when**: Test file has TypeScript types
  - **Verify**: `npx tsc --noEmit tests/e2e/create-trip.spec.ts 2>&1 | head -5`
  - **Commit**: `feat(e2e): add TypeScript types to create-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for TypeScript integration

- [ ] T033 [P] [US-2] Add TypeScript types to edit-trip.spec.ts
  - **Do**:
    1. Add explicit Page type import
    2. Add type annotations to test function parameters
    3. Add interface for TripData
  - **Files**: `tests/e2e/edit-trip.spec.ts`
  - **Done when**: Test file has TypeScript types
  - **Verify**: `npx tsc --noEmit tests/e2e/edit-trip.spec.ts 2>&1 | head -5`
  - **Commit**: `feat(e2e): add TypeScript types to edit-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for TypeScript integration

- [ ] T034 [P] [US-3] Add TypeScript types to delete-trip.spec.ts
  - **Do**:
    1. Add explicit Page type import
    2. Add type annotations to test function parameters
    3. Add interface for TripData
  - **Files**: `tests/e2e/delete-trip.spec.ts`
  - **Done when**: Test file has TypeScript types
  - **Verify**: `npx tsc --noEmit tests/e2e/delete-trip.spec.ts 2>&1 | head -5`
  - **Commit**: `feat(e2e): add TypeScript types to delete-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for TypeScript integration

### Phase 2 Quality Checkpoint

- [ ] T035 [VERIFY] Phase 2 Quality checkpoint: TypeScript compilation
  - **Do**: Run TypeScript compilation check on all test files
  - **Verify**: `npx tsc --noEmit playwright.config.ts auth.setup.ts globalTeardown.ts tests/e2e/*.ts 2>&1 | head -30`
  - **Done when**: All TypeScript files compile without errors
  - **Commit**: `chore(e2e): pass Phase 2 quality checkpoint`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for type checking

## Phase 3: Polish (8 tasks)

### JSDoc and Comments

- [ ] T036 [P] [US-1] Add JSDoc comments to trips-helpers.ts functions
  - **Do**:
    1. Add JSDoc to navigateToPanel: describes navigation to EV Trip Planner panel
    2. Add JSDoc to createTestTrip: describes parameters
    3. Add JSDoc to deleteTestTrip: describes trip cleanup
    4. Add @param and @returns tags
  - **Files**: `tests/e2e/trips-helpers.ts`
  - **Done when**: All functions have JSDoc comments
  - **Verify**: `cat tests/e2e/trips-helpers.ts | grep -c "JSDoc\|\\*\\*" | xargs -I {} test {} -ge 3 && echo "OK"`
  - **Commit**: `docs(e2e): add JSDoc comments to trips-helpers.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for code documentation patterns

- [ ] T037 [P] [US-1] Add comments to create-trip.spec.ts explaining flow
  - **Do**:
    1. Add header comment explaining test purpose
    2. Add inline comments for each step
    3. Document expected values: km=50, kwh=15
  - **Files**: `tests/e2e/create-trip.spec.ts`
  - **Done when**: Test has explanatory comments
  - **Verify**: `cat tests/e2e/create-trip.spec.ts | grep -c "//" | xargs -I {} test {} -ge 5 && echo "OK"`
  - **Commit**: `docs(e2e): add comments to create-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for code documentation

- [ ] T038 [P] [US-2] Add comments to edit-trip.spec.ts explaining flow
  - **Do**:
    1. Add header comment explaining test purpose
    2. Add inline comments for each step
    3. Document expected values: km changes from 30 to 35
  - **Files**: `tests/e2e/edit-trip.spec.ts`
  - **Done when**: Test has explanatory comments
  - **Verify**: `cat tests/e2e/edit-trip.spec.ts | grep -c "//" | xargs -I {} test {} -ge 5 && echo "OK"`
  - **Commit**: `docs(e2e): add comments to edit-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for code documentation

- [ ] T039 [P] [US-3] Add comments to delete-trip.spec.ts explaining flow
  - **Do**:
    1. Add header comment explaining test purpose
    2. Add inline comments for each step
    3. Document expected dialog text
  - **Files**: `tests/e2e/delete-trip.spec.ts`
  - **Done when**: Test has explanatory comments
  - **Verify**: `cat tests/e2e/delete-trip.spec.ts | grep -c "//" | xargs -I {} test {} -ge 5 && echo "OK"`
  - **Commit**: `docs(e2e): add comments to delete-trip.spec.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for code documentation

- [ ] T040 [P] [US-0] Add comments to auth.setup.ts explaining Config Flow
  - **Do**:
    1. Add header comment explaining auth.setup.ts purpose
    2. Add comments for each Config Flow step (1-5)
    3. Document trusted_networks bypass mechanism
  - **Files**: `auth.setup.ts`
  - **Done when**: auth.setup.ts has explanatory comments
  - **Verify**: `cat auth.setup.ts | grep -c "//" | xargs -I {} test {} -ge 10 && echo "OK"`
  - **Commit**: `docs(e2e): add comments to auth.setup.ts`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for code documentation

### Selector Verification

- [ ] T041 [P] [US-1] Verify selector patterns follow homeassistant-selector-map rules
  - **Do**:
    1. Review all selectors in trips-helpers.ts and test files
    2. Ensure NO use of >> pierce syntax
    3. Ensure NO XPath or CSS class selectors
    4. Ensure all selectors use getByRole, getByLabel, or getByTestId
  - **Files**: `tests/e2e/trips-helpers.ts`, `tests/e2e/*.spec.ts`, `auth.setup.ts`
  - **Done when**: All selectors follow web-first locator pattern
  - **Verify**: `grep -r ">>\|xpath\|getByCss" tests/e2e/ auth.setup.ts && echo "FOUND_FORBIDDEN" || echo "OK"`
  - **Commit**: `refactor(e2e): verify selectors follow homeassistant-selector-map rules`
  - **Skills**:
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for selector hierarchy

- [ ] T042 [P] [US-1] Verify navigation patterns follow SPA rules
  - **Do**:
    1. Review all navigation in trips-helpers.ts and test files
    2. Ensure ONLY page.goto('/') is used as entry point
    3. Ensure NO direct goto to internal panels
    4. Ensure sidebar navigation is used for panel access
  - **Files**: `tests/e2e/trips-helpers.ts`, `tests/e2e/*.spec.ts`, `auth.setup.ts`
  - **Done when**: All navigation follows SPA pattern
  - **Verify**: `grep -r "goto('/ev\|goto('/config" tests/e2e/ auth.setup.ts && echo "FOUND_FORBIDDEN" || echo "OK"`
  - **Commit**: `refactor(e2e): verify navigation follows SPA rules`
  - **Skills**:
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for SPA navigation rules

- [ ] T043 [P] [US-1] Add README.md to tests/e2e with test documentation
  - **Do**:
    1. Create `tests/e2e/README.md`
    2. Document test structure and purpose
    3. Document test values for each test
    4. Document how to run tests locally vs in CI
  - **Files**: `tests/e2e/README.md`
  - **Done when**: README.md exists with documentation
  - **Verify**: `test -f tests/e2e/README.md && echo "OK"`
  - **Commit**: `docs(e2e): add README.md to tests/e2e`
  - **Skills**:
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for test documentation patterns

## Phase 4: Quality Gates (6 tasks)

### GitHub Actions Configuration

- [ ] T044 [US-0] Create trusted_networks configuration.yaml for HA service
  - **Do**:
    1. Create `tests/ha-manual/configuration.yaml` with trusted_networks auth provider
    2. Add auth_providers section with trusted_networks type
    3. Include trusted_networks: 127.0.0.1, 172.17.0.0/16
    4. Set allow_bypass_login: true
  - **Files**: `tests/ha-manual/configuration.yaml`
  - **Done when**: configuration.yaml has trusted_networks auth provider
  - **Verify**: `cat tests/ha-manual/configuration.yaml | grep -A5 "auth_providers" | grep -q "trusted_networks" && echo "OK"`
  - **Commit**: `fix(e2e): add trusted_networks configuration.yaml`
  - **Skills**:
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for trusted_networks configuration

- [ ] T045 [US-0] Update GitHub Actions workflow to mount configuration.yaml
  - **Do**:
    1. Update `.github/workflows/playwright.yml`
    2. Add volume mount for configuration.yaml
  - **Files**: `.github/workflows/playwright.yml`
  - **Done when**: workflow has configuration.yaml volume mount
  - **Verify**: `cat .github/workflows/playwright.yml | grep -q "configuration.yaml" && echo "OK"`
  - **Commit**: `fix(e2e): mount trusted_networks configuration.yaml in HA service`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for GitHub Actions service container configuration

### Quality Checkpoints

- [ ] T046 [VERIFY] V1 Quality checkpoint: lint and typecheck
  - **Do**: Run lint and typecheck on all E2E files
  - **Verify**: `npx eslint playwright.config.ts auth.setup.ts globalTeardown.ts tests/e2e/*.ts && npx tsc --noEmit`
  - **Done when**: Both lint and typecheck pass
  - **Commit**: `chore(e2e): pass quality checkpoint`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for quality gate verification

- [ ] T047 [VERIFY] V2 Full local CI
  - **Do**: Run complete local CI suite
  - **Verify**: `npx tsc --noEmit && npx eslint playwright.config.ts auth.setup.ts globalTeardown.ts tests/e2e/*.ts && npx playwright test tests/e2e/ --reporter=list`
  - **Done when**: All commands pass
  - **Commit**: `chore(e2e): pass full local CI`
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for full CI suite

- [ ] T048 [VERIFY] V3 AC checklist
  - **Do**: Verify all acceptance criteria from requirements.md
  - **Verify**: All AC files exist and tests cover all AC
  - **Done when**: All acceptance criteria have corresponding test coverage
  - **Commit**: None
  - **Skills**:
    - **e2e-testing-patterns** - Read `.claude/skills/e2e-testing-patterns/SKILL.md` for acceptance criteria verification

### VE Tasks (E2E Verification via qa-engineer)

- [ ] T049 [VERIFY] VE0 UI Map Init: build selector map
  - **Do**: Load `ui-map-init` skill and follow VE0 protocol
  - **Verify**: `test -f ui-map.local.md && echo "MAP_EXISTS"`
  - **Done when**: Map written or confirmed current
  - **Commit**: None
  - **Skills**:
    - **homeassistant-selector-map** - Read `/home/malka/.claude/plugins/marketplaces/smart-ralph/plugins/ralph-specum/skills/e2e/examples/homeassistant-selector-map/SKILL.md` for UI map initialization

- [ ] T050 [VERIFY] VE1 E2E startup: launch infrastructure
  - **Do**:
    1. Start Home Assistant service container in background
    2. Record PID to /tmp/ve-pids.txt
    3. Wait for ready signal (HTTP 200 on port 8123)
  - **Verify**: `curl -sf http://localhost:8123/ && echo "HA_READY"`
  - **Done when**: Home Assistant is running and responding
  - **Commit**: None
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for infrastructure startup

- [ ] T051 [VERIFY] VE2 E2E check: verify CRUD user flows
  - **Do**:
    1. Load selectors from ui-map.local.md
    2. Execute create-trip flow
    3. Execute edit-trip flow
    4. Execute delete-trip flow
    5. Verify expected outputs
  - **Verify**: All 3 CRUD flows execute successfully
  - **Done when**: All CRUD flows produce expected results
  - **Commit**: None
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for E2E test execution

- [ ] T052 [VERIFY] VE3 E2E cleanup: tear down infrastructure
  - **Do**:
    1. Read PIDs from /tmp/ve-pids.txt
    2. Send SIGTERM to each process
    3. Remove /tmp/ve-pids.txt
    4. Verify port 8123 is free
  - **Verify**: `! lsof -ti :8123 && echo "PORT_FREE"`
  - **Done when**: All VE processes terminated, ports freed
  - **Commit**: None
  - **Skills**:
    - **playwright-best-practices** - Read `.claude/skills/playwright-best-practices/SKILL.md` for cleanup verification

## Notes

### POC Shortcuts
- Config Flow has 5 steps (user, sensors, emhass, presence, notifications) per config_flow.py
- charging_sensor in presence step auto-selects if not provided
- Vehicle ID hardcoded as "test_vehicle" for CI consistency

### Constitution Alignment
- C§4.2 (Naming): Web-first locators follow semantic naming (getByRole, getByLabel)
- C§4.3 (Error handling): Dialog handling with proper error messages
- C§5.1 (Testing): E2E tests for CRUD operations
- C§5.3 (Security): trusted_networks bypass avoids storing credentials

### Technical Debt
- Tests run with 1 worker to avoid HA port conflicts
- Dialog text verification may break if HA translations change
- May need retry logic for flaky panel loads in CI
