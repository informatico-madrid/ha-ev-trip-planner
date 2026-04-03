# Tasks: E2E Test Suite for EV Trip Planner

## Phase 1: Make It Work (POC)

Focus: Validate the E2E test infrastructure works end-to-end with ephemeral HA.

- [x] 1.1 [P] Create playwright.config.ts
  - **Do**:
    1. Create `playwright.config.ts` at repo root with: `testDir: './tests/e2e'`, `workers: 1`, `retries: 0`, `fullyParallel: false`
    2. Reference `globalSetup: 'tests/global.setup.ts'` and `globalTeardown: 'tests/global.teardown.ts'`
    3. Set `baseURL: 'http://localhost:8123'`
    4. Chromium-only project using `devices['Desktop Chrome']`
    5. Add `use: { storageState: 'playwright/.auth/user.json' }` to project
    6. Add `webServer` rejected since global.setup.ts handles server startup
  - **Files**: `playwright.config.ts`
  - **Done when**: Config file exists and references existing global.setup.ts/global.teardown.ts
  - **Verify**: `grep -l 'globalSetup.*global.setup' playwright.config.ts && echo PASS`
  - **Commit**: `feat(e2e): add playwright.config.ts with globalSetup and Chromium project`
  - _Requirements: FR-1_
  - _Design: playwright.config.ts section_

- [x] 1.2 [P] Create tests/e2e/pages/ConfigFlowPage.ts
  - **Do**:
    1. Create `tests/e2e/pages/` directory
    2. Create `ConfigFlowPage` class with: `page: Page`, locators for `addIntegrationBtn`, `searchInput`, `vehicleNameInput`, `submitBtn`
    3. Methods: `navigateToIntegrations()`, `addIntegration(name)`, `fillVehicleName(name)`, `submit()`, `waitForIntegrationComplete()`, `waitForPanelInSidebar()`
  - **Files**: `tests/e2e/pages/ConfigFlowPage.ts`
  - **Done when**: POM class exportsable with all methods; uses HA UI selectors from design
  - **Verify**: `grep -c 'async.*\(\)' tests/e2e/pages/ConfigFlowPage.ts | grep -q '^[4-9]' && echo PASS`
  - **Commit**: `feat(e2e): add ConfigFlowPage POM`
  - _Requirements: FR-3_
  - _Design: ConfigFlowPage.ts section_

- [x] 1.3 [P] Create tests/e2e/pages/EVTripPlannerPage.ts
  - **Do**:
    1. Create `EVTripPlannerPage` class with Shadow DOM pierce combinator selectors
    2. Locators via pierce: `addTripBtn`, `tripsList`, `tripFormOverlay`, `tripTypeSelect`, `tripDaySelect`, `tripTimeInput`, `tripKmInput`, `tripKwhInput`, `tripDescriptionInput`, `tripSubmitBtn`
    3. Methods: `openFromSidebar()`, `openAddTripForm()`, `createRecurringTrip(opts)`, `expectTripVisible(tripId)`, `deleteTrip(tripId)`
  - **Files**: `tests/e2e/pages/EVTripPlannerPage.ts`
  - **Done when**: POM uses `>>` pierce combinator for all Shadow DOM selectors
  - **Verify**: `grep -c '>>' tests/e2e/pages/EVTripPlannerPage.ts | grep -q '^[5-9]' && echo PASS`
  - **Commit**: `feat(e2e): add EVTripPlannerPage POM with Shadow DOM pierce selectors`
  - _Requirements: FR-4, FR-5_
  - _Design: EVTripPlannerPage.ts section_

- [ ] 1.4 [P] Create tests/e2e/auth.setup.ts
  - **Do**:
    1. Create `tests/e2e/auth.setup.ts` as a Playwright `setup` file (not globalSetup)
    2. Read server info from `playwright/.auth/server-info.json`
    3. Navigate to HA, run full Config Flow: integrations page -> Add Integration -> "EV Trip Planner" -> vehicle_name -> Submit x 5 steps
    4. Verify sidebar shows "EV Trip Planner" after completion
    5. Save storageState to `playwright/.auth/user.json`
  - **Files**: `tests/e2e/auth.setup.ts`
  - **Done when**: File runs Config Flow UI end-to-end and saves storageState
  - **Verify**: `grep -c 'storageState' tests/e2e/auth.setup.ts && echo PASS`
  - **Commit**: `feat(e2e): add auth.setup.ts for Config Flow authentication`
  - _Requirements: FR-2, AC-1.1-AC-1.6_
  - _Design: auth.setup.ts section_

- [x] 1.5 [P] Create tests/e2e/vehicle.spec.ts
  - **Do**:
    1. Create `tests/e2e/vehicle.spec.ts` with `test.describe('Vehicle Creation and Panel')`
    2. `beforeEach`: load storageState from auth file, instantiate POMs
    3. Test: run Config Flow -> verify panel in sidebar -> click sidebar link -> verify panel URL `/ev-trip-planner-*` -> verify addTripBtn visible
    4. `afterEach`: navigate to integrations page, find integration row by vehicleName, click Delete to remove
  - **Files**: `tests/e2e/vehicle.spec.ts`
  - **Done when**: Test creates vehicle via Config Flow and verifies panel opens; cleanup removes integration
  - **Verify**: `grep -c 'afterEach\|afterAll' tests/e2e/vehicle.spec.ts && echo PASS`
  - **Commit**: `feat(e2e): add vehicle.spec.ts for US-1 and US-2`
  - _Requirements: FR-6, AC-1.1-AC-1.6, AC-2.1-AC-2.4_
  - _Design: vehicle.spec.ts section_

- [ ] 1.6 [P] Create tests/e2e/trip.spec.ts
  - **Do**:
    1. Create `tests/e2e/trip.spec.ts` with `test.describe('Trip Creation')`
    2. `beforeEach`: load storageState, create vehicle via Config Flow (same flow as vehicle.spec.ts), navigate to panel
    3. Test 1: create recurring trip - open form, fill recurring trip fields, submit, verify form closes and trip card appears with correct text
    4. Test 2: create punctual trip - select punctual type, fill punctual fields, submit, verify card appears
    5. `afterEach`: delete trips via panel UI (click delete buttons), then remove integration via Config Flow
  - **Files**: `tests/e2e/trip.spec.ts`
  - **Done when**: Tests create trips via Shadow DOM form and verify persistence; cleanup deletes data
  - **Verify**: `grep -c 'afterEach' tests/e2e/trip.spec.ts && echo PASS`
  - **Commit**: `feat(e2e): add trip.spec.ts for US-3, US-4, and US-5`
  - _Requirements: FR-7, FR-8, AC-3.1-AC-3.7, AC-4.1-AC-4.4, AC-5.1-AC-5.4_
  - _Design: trip.spec.ts section_

- [ ] 1.7 [VERIFY] Quality checkpoint: TypeScript compiles
  - **Do**: Run `npx tsc --noEmit --project tsconfig.json` to verify TypeScript types
  - **Verify**: Exit code 0 from tsc
  - **Done when**: No TypeScript errors in created files
  - **Commit**: `chore(e2e): fix TypeScript errors in e2e test files` (only if fixes needed)

- [ ] 1.8 [VERIFY] POC verification: Run tests against ephemeral HA
  - **Do**:
    1. Start ephemeral HA: `npx playwright test tests/e2e/ --dry-run` to verify config loads (global setup starts server)
    2. Or run subset: `npx playwright test tests/e2e/vehicle.spec.ts --timeout=120000`
  - **Done when**: Ephemeral HA starts, Config Flow completes, tests run
  - **Verify**: Test output shows Config Flow completing without errors
  - **Commit**: None (POC validation)

## Phase 2: Refactoring

After POC validated, clean up POMs and test structure.

- [ ] 2.1 Refactor EVTripPlannerPage.deleteTrip method
  - **Do**: Fix `deleteTrip` method in EVTripPlannerPage - the design had `page.on('dialog', ...)` inside an instance method which is wrong. Move dialog handler to test level or use page.dialog event properly.
  - **Files**: `tests/e2e/pages/EVTripPlannerPage.ts`, `tests/e2e/trip.spec.ts`
  - **Done when**: Dialog handling works correctly in afterEach cleanup
  - **Verify**: `npx tsc --noEmit tests/e2e/trip.spec.ts`
  - **Commit**: `fix(e2e): fix dialog handler in trip deletion`
  - _Design: Error Handling section_

- [ ] 2.2 Refactor trip.spec.ts cleanup to use API-based deletion
  - **Do**: Replace UI-based trip deletion with `DELETE /api/states/sensor.ev_trip_planner_{vehicle_id}_trips` API call in afterEach
  - **Files**: `tests/e2e/trip.spec.ts`
  - **Done when**: Cleanup uses API instead of clicking delete buttons one-by-one
  - **Verify**: `grep -c 'DELETE.*api/states' tests/e2e/trip.spec.ts`
  - **Commit**: `refactor(e2e): use API for trip cleanup in afterEach`

- [ ] 2.3 [VERIFY] Quality checkpoint: lint + typecheck
  - **Do**: Run `npx tsc --noEmit` and `npm run lint` if available
  - **Verify**: All commands exit 0
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(e2e): pass quality checkpoint` (only if fixes needed)

## Phase 3: Testing

Add additional tests or fix integration issues found during Phase 1.

- [ ] 3.1 Fix any selectors that broke during POC run
  - **Do**: If tests failed in Phase 1 VE step, fix the broken selectors based on actual HA UI structure
  - **Files**: `tests/e2e/pages/ConfigFlowPage.ts`, `tests/e2e/pages/EVTripPlannerPage.ts`
  - **Done when**: All selectors match actual HA UI elements
  - **Verify**: Tests run without selector timeouts
  - **Commit**: `fix(e2e): update selectors for actual HA UI structure`

- [ ] 3.2 [VERIFY] Quality checkpoint: run full test suite
  - **Do**: Run `npx playwright test tests/e2e/ --timeout=300000`
  - **Verify**: All tests pass
  - **Done when**: Full suite passes without errors
  - **Commit**: `chore(e2e): full suite passes` (only if fixes needed)

## Phase 4: Quality Gates

Final validation before PR.

- [ ] 4.1 [VERIFY] Full local CI: typecheck + lint + tests
  - **Do**: Run in sequence: `npx tsc --noEmit` then `npx playwright test tests/e2e/`
  - **Verify**: All commands exit 0
  - **Done when**: Build succeeds, all tests pass
  - **Commit**: `chore(e2e): pass local CI` (only if fixes needed)

- [ ] 4.2 [VERIFY] CI pipeline passes
  - **Do**: Push branch and verify GitHub Actions workflow passes
  - **Verify**: `gh run list --workflow=playwright.yml --status=completed` shows success
  - **Done when**: All CI checks green
  - **Commit**: None

- [ ] 4.3 [VERIFY] AC checklist
  - **Do**: Read requirements.md, verify each acceptance criteria is satisfied:
    - FR-1: playwright.config.ts references global.setup/global.teardown and Chromium only
    - FR-2: auth.setup.ts runs Config Flow and saves storageState
    - FR-3: ConfigFlowPage POM exists with all methods
    - FR-4: EVTripPlannerPage POM exists with all methods
    - FR-5: Shadow DOM selectors use pierce combinator `>>`
    - FR-6: vehicle.spec.ts creates vehicle and verifies panel opens
    - FR-7: trip.spec.ts creates trip and verifies listing
    - FR-8: afterEach cleanup in both spec files
    - FR-9: CI workflow exists and runs on PR
  - **Verify**: Each grep/find command returns positive
  - **Done when**: All 9 functional requirements confirmed implemented
  - **Commit**: None

- [ ] VE1 [VERIFY] E2E startup: verify ephemeral HA starts correctly
  - **Do**:
    1. Verify `tests/global.setup.ts` exists and is correct
    2. Verify `playwright.config.ts` globalSetup points to it
    3. Verify `playwright/.auth/` directory structure will be created
  - **Verify**: `ls tests/global.setup.ts && grep 'globalSetup' playwright.config.ts && echo VE1_PASS`
  - **Done when**: Ephemeral HA startup configured correctly
  - **Commit**: None

- [ ] VE2 [VERIFY] E2E check: run vehicle.spec.ts as smoke test
  - **Do**:
    1. Run `npx playwright test tests/e2e/vehicle.spec.ts --timeout=180000`
    2. Verify Config Flow completes and panel opens
    3. Check that afterEach cleanup runs without errors
  - **Verify**: Test passes with exit code 0
  - **Done when**: Smoke test passes against real ephemeral HA
  - **Commit**: None

- [ ] VE3 [VERIFY] E2E cleanup: verify server shutdown works
  - **Do**:
    1. Verify `tests/global.teardown.ts` exists
    2. Verify it cleans up server-info.json
    3. After VE2 tests complete, check no orphaned HA processes
  - **Verify**: `ls tests/global.teardown.ts && echo VE3_PASS`
  - **Done when**: Cleanup configured correctly
  - **Commit**: None

## Phase 5: PR Lifecycle

- [ ] 5.1 Verify branch and create PR
  - **Do**:
    1. Verify current branch is a feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin e2e-trip-crud-tests`
    3. Create PR using gh CLI: `gh pr create --title "feat(e2e): add Playwright E2E test suite for EV Trip Planner" --body "$(cat <<'EOF'
## Summary
- Add playwright.config.ts with globalSetup/globalTeardown and Chromium-only project
- Add tests/e2e/auth.setup.ts for Config Flow UI authentication
- Add tests/e2e/pages/ConfigFlowPage.ts POM for HA Config Flow
- Add tests/e2e/pages/EVTripPlannerPage.ts POM for EV Trip Planner panel
- Add tests/e2e/vehicle.spec.ts for US-1 (install) and US-2 (view panel)
- Add tests/e2e/trip.spec.ts for US-3 (create trip), US-4 (verify listing), US-5 (cleanup)

## Test plan
- [ ] `npx playwright test tests/e2e/` passes in CI
- [ ] Config Flow completes successfully
- [ ] Trip creation and verification works
- [ ] Cleanup removes all test data

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"`
  - **Verify**: PR created successfully
  - **Done when**: PR exists with correct title and description
  - **Commit**: None

- [ ] 5.2 Monitor CI and address failures
  - **Do**:
    1. Watch CI: `gh run watch`
    2. If CI fails, read logs and fix issues
    3. Push fixes: `git push`
    4. Re-verify: `gh run watch`
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: All CI checks pass
  - **Commit**: `fix(e2e): <issue> from CI review`

## Notes

- **POC shortcuts taken**: Phase 1 accepts hardcoded selectors that may need adjustment after first run against real HA; cleanup uses UI-based deletion first, then refactored to API in Phase 2
- **Production TODOs**: API-based cleanup (Phase 2.2), dialog handler fix (Phase 2.1)
- **VE strategy**: Since this spec IS the E2E test suite, VE tasks verify the test infrastructure itself works by running a smoke test against ephemeral HA
- **Config Flow fields**: Based on `config_flow.py` analysis; may need field name verification against actual HA UI
