# Tasks: E2E Trip CRUD Tests

## Phase 1: Red-Green-Yellow Cycles

Focus: Test-driven implementation. Each trip CRUD operation follows RED-GREEN-YELLOW triplet pattern.

### US-1: Create Recurring Trip

- [ ] 1.1 [RED] Failing test: should create recurring trip with all fields
  - **Do**: Write test that calls createRecurringTrip() with day, time, km, kwh, description and verifies trip appears in .trips-list with correct values
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Test exists and fails with "TripsPage not defined" error
  - **Verify**: `npx playwright test trips.spec.ts --grep "create recurring" 2>&1 | grep -E "FAIL|error"`
  - **Commit**: `test(trips): red - failing test for create recurring trip`
  - _Requirements: US-1, AC-1.1-AC-1.11_
  - _Design: TripsPage class structure_

- [ ] 1.2 [GREEN] Pass test: implement createRecurringTrip in TripsPage
  - **Do**: Create TripsPage class with constructor taking page and vehicleId, implement createRecurringTrip method using Shadow DOM traversal pattern (ev-trip-planner-panel >> #selector)
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Test passes (TripsPage.createRecurringTrip opens form, fills fields, submits, returns tripId)
  - **Verify**: `npx playwright test trips.spec.ts --grep "create recurring"`
  - **Commit**: `feat(trips): implement createRecurringTrip`
  - _Requirements: US-1, AC-1.1-AC-1.11_
  - _Design: Shadow DOM traversal, form fill sequence_

- [ ] 1.3 [YELLOW] Refactor: extract TripData interfaces to top of file
  - **Do**: Move RecurringTripData and PunctualTripData interfaces to top-level exports, add JSDoc comments
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Code is organized, interfaces are reusable, tests still pass
  - **Verify**: `npx playwright test trips.spec.ts --grep "create recurring"`
  - **Commit**: `refactor(trips): extract TripData interfaces`

- [ ] V1 [VERIFY] Quality checkpoint: lint and typecheck
  - **Do**: Run typecheck on trips.page.ts
  - **Verify**: `npx tsc --noEmit tests/e2e/pages/trips.page.ts 2>&1; echo "TC_EXIT:$?"`
  - **Done when**: No type errors, no lint errors
  - **Commit**: `chore(trips): pass quality checkpoint`

### US-2: Create Punctual Trip

- [ ] 1.4 [RED] Failing test: should create punctual trip with datetime
  - **Do**: Write test that calls createPunctualTrip() with datetime, km, kwh, description and verifies trip appears with correct datetime values
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Test exists and fails with "createPunctualTrip not defined"
  - **Verify**: `npx playwright test trips.spec.ts --grep "create punctual" 2>&1 | grep -E "FAIL|error"`
  - **Commit**: `test(trips): red - failing test for create punctual trip`
  - _Requirements: US-2, AC-2.1-AC-2.8_
  - _Design: TripsPage.createPunctualTrip method_

- [ ] 1.5 [GREEN] Pass test: implement createPunctualTrip in TripsPage
  - **Do**: Implement createPunctualTrip method that selects "puntual" type, fills datetime-local input, km, kwh, description and submits form
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Test passes (form opens, punctual type selected, datetime filled, trip created)
  - **Verify**: `npx playwright test trips.spec.ts --grep "create punctual"`
  - **Commit**: `feat(trips): implement createPunctualTrip`
  - _Requirements: US-2, AC-2.1-AC-2.8_
  - _Design: datetime-local input handling_

- [ ] 1.6 [YELLOW] Refactor: share form-open logic between createRecurring and createPunctual
  - **Do**: Extract common _openForm method that handles add-trip-btn click and form overlay visibility
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Code duplication reduced, tests still pass
  - **Verify**: `npx playwright test trips.spec.ts --grep "create"`
  - **Commit**: `refactor(trips): extract _openForm helper`

- [ ] V2 [VERIFY] Quality checkpoint: verify both create tests pass
  - **Do**: Run typecheck and both create tests
  - **Verify**: `npx tsc --noEmit tests/e2e/pages/trips.page.ts && npx playwright test trips.spec.ts --grep "create"`
  - **Done when**: All commands pass
  - **Commit**: `chore(trips): pass quality checkpoint`

### US-3: Edit Trip

- [ ] 1.7 [RED] Failing test: should edit existing trip
  - **Do**: Write test that creates a recurring trip, clicks edit button, verifies form pre-fills with "Guardar Cambios" button text, modifies km/time, saves and verifies updated values
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Test exists and fails with "editTrip not defined"
  - **Verify**: `npx playwright test trips.spec.ts --grep "edit" 2>&1 | grep -E "FAIL|error"`
  - **Commit**: `test(trips): red - failing test for edit trip`
  - _Requirements: US-3, AC-3.1-AC-3.6_
  - _Design: TripsPage.editTrip method_

- [ ] 1.8 [GREEN] Pass test: implement editTrip in TripsPage
  - **Do**: Implement editTrip method that locates trip card by data-trip-id, clicks edit button, fills updated fields, clicks submit
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Test passes (edit form opens, updates saved, card reflects new values)
  - **Verify**: `npx playwright test trips.spec.ts --grep "edit"`
  - **Commit**: `feat(trips): implement editTrip`
  - _Requirements: US-3, AC-3.1-AC-3.6_
  - _Design: data-trip-id based trip card lookup_

- [ ] 1.9 [YELLOW] Refactor: add cancel edit test coverage
  - **Do**: Add test for cancel button (.btn-secondary) discards changes
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Cancel test passes, edit test still passes
  - **Verify**: `npx playwright test trips.spec.ts --grep "edit|cancel"`
  - **Commit**: `test(trips): add cancel edit test`

- [ ] V3 [VERIFY] Quality checkpoint: verify edit tests pass
  - **Do**: Run typecheck and edit tests
  - **Verify**: `npx tsc --noEmit tests/e2e/pages/trips.page.ts && npx playwright test trips.spec.ts --grep "edit"`
  - **Done when**: All commands pass
  - **Commit**: `chore(trips): pass quality checkpoint`

### US-4: Delete Trip

- [ ] 1.10 [RED] Failing test: should delete trip with dialog acceptance
  - **Do**: Write test that creates a trip, sets up dialog handler to accept, clicks delete button, verifies trip removed from list
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Test exists and fails with "deleteTrip not defined"
  - **Verify**: `npx playwright test trips.spec.ts --grep "delete" 2>&1 | grep -E "FAIL|error"`
  - **Commit**: `test(trips): red - failing test for delete trip`
  - _Requirements: US-4, AC-4.1-AC-4.5_
  - _Design: TripsPage.deleteTrip method_

- [ ] 1.11 [GREEN] Pass test: implement deleteTrip in TripsPage
  - **Do**: Implement deleteTrip method that registers page.on('dialog') handler before clicking delete button, accepts/dismisses dialog, removes trip
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Test passes (dialog handled, trip removed from .trips-list)
  - **Verify**: `npx playwright test trips.spec.ts --grep "delete"`
  - **Commit**: `feat(trips): implement deleteTrip`
  - _Requirements: US-4, AC-4.1-AC-4.5_
  - _Design: dialog handling pattern_

- [ ] 1.12 [YELLOW] Refactor: add dismiss dialog test
  - **Do**: Add test that dismisses confirmation dialog and verifies trip remains
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Dismiss test passes, delete test still passes
  - **Verify**: `npx playwright test trips.spec.ts --grep "delete"`
  - **Commit**: `test(trips): add dismiss dialog test`

- [ ] V4 [VERIFY] Quality checkpoint: verify all CRUD tests pass
  - **Do**: Run typecheck and all CRUD tests
  - **Verify**: `npx tsc --noEmit tests/e2e/pages/trips.page.ts && npx playwright test trips.spec.ts`
  - **Done when**: All commands pass
  - **Commit**: `chore(trips): pass quality checkpoint`

### Helper Methods and Cleanup

- [ ] 1.13 [GREEN] Implement getTripCount and waitForTrip helpers
  - **Do**: Implement getTripCount() returning count of .trip-card elements, waitForTrip(tripId) that waits for card with specific data-trip-id
  - **Files**: tests/e2e/pages/trips.page.ts
  - **Done when**: Helper methods work correctly
  - **Verify**: `npx playwright test trips.spec.ts`
  - **Commit**: `feat(trips): add getTripCount and waitForTrip helpers`

- [ ] 1.14 [GREEN] Implement cleanupTrips for test independence
  - **Do**: Implement cleanupTrips() that gets all tripIds and deletes them, call in test.afterEach()
  - **Files**: tests/e2e/trips.spec.ts, tests/e2e/pages/trips.page.ts
  - **Done when**: Each test cleans up its own trips, tests can run in any order
  - **Verify**: `npx playwright test trips.spec.ts --grep "cleanup" || npx playwright test trips.spec.ts`
  - **Commit**: `feat(trips): add cleanupTrips for test independence`

- [ ] 1.15 [GREEN] Export TripsPage from pages/index.ts
  - **Do**: Add TripsPage export to tests/e2e/pages/index.ts
  - **Files**: tests/e2e/pages/index.ts
  - **Done when**: TripsPage is importable from pages index
  - **Verify**: `grep "TripsPage" tests/e2e/pages/index.ts`
  - **Commit**: `feat(trips): export TripsPage from pages index`

- [ ] V5 [VERIFY] Quality checkpoint: full CRUD suite passes
  - **Do**: Run typecheck and all tests
  - **Verify**: `npx tsc --noEmit tests/e2e/pages/trips.page.ts && npx playwright test trips.spec.ts`
  - **Done when**: All tests pass
  - **Commit**: `chore(trips): pass full CRUD suite`

## Phase 2: Additional Testing

Focus: Edge cases and integration scenarios beyond the happy path.

- [ ] 2.1 Add empty state verification test
  - **Do**: Test that .no-trips element shows when last trip is deleted
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Empty state test passes
  - **Verify**: `npx playwright test trips.spec.ts --grep "empty"`
  - **Commit**: `test(trips): verify empty state after last delete`
  - _Requirements: AC-4.5_

- [ ] 2.2 Add form validation test (submit empty form)
  - **Do**: Test that submitting form without required fields shows validation errors or prevents submission
  - **Files**: tests/e2e/trips.spec.ts
  - **Done when**: Validation test passes
  - **Verify**: `npx playwright test trips.spec.ts --grep "validation"`
  - **Commit**: `test(trips): add form validation test`
  - _Requirements: FR-7_

- [ ] 2.3 [VERIFY] Quality checkpoint: additional tests pass
  - **Do**: Run all tests including new edge case tests
  - **Verify**: `npx playwright test trips.spec.ts`
  - **Done when**: All tests pass
  - **Commit**: `chore(trips): pass edge case tests`

## Phase 3: Quality Gates

- [ ] 3.1 [VERIFY] Full local CI: lint, typecheck, test
  - **Do**: Run complete local CI suite: typecheck + all tests
  - **Verify**: `npx tsc --noEmit tests/e2e/pages/trips.page.ts && npx playwright test trips.spec.ts`
  - **Done when**: Build succeeds, all tests pass
  - **Commit**: `chore(trips): pass local CI`

- [ ] 3.2 [VERIFY] CI pipeline passes
  - **Do**: Push branch and verify GitHub Actions passes
  - **Verify**: `gh pr checks --watch` or `gh pr checks`
  - **Done when**: CI pipeline passes
  - **Commit**: None (CI verifies)

- [ ] 3.3 [VERIFY] AC checklist: verify all acceptance criteria satisfied
  - **Do**: Read requirements.md and grep codebase for AC implementation evidence
  - **Verify**: Grep for data-trip-id, trip-card, trip-form-overlay, btn-primary, trip-type selectors in trips.page.ts and trips.spec.ts
  - **Done when**: All ACs have corresponding test code
  - **Commit**: None

## Phase 4: PR Lifecycle

- [ ] 4.1 Create PR and verify CI
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin <branch-name>`
    3. Create PR using gh CLI: `gh pr create --title "feat(e2e): add trip CRUD tests" --body "$(cat <<'EOF'
## Summary
- Add Playwright E2E tests for trip CRUD operations (Create, Edit, Delete)
- Create TripsPage Page Object with Shadow DOM traversal
- Tests use independent cleanup via test.afterEach()

## Test plan
- [ ] US-1: Create recurring trip - AC-1.1 through AC-1.11
- [ ] US-2: Create punctual trip - AC-2.1 through AC-2.8
- [ ] US-3: Edit trip - AC-3.1 through AC-3.6
- [ ] US-4: Delete trip - AC-4.1 through AC-4.5
- [ ] All tests pass in CI pipeline

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"`
  - **Verify**: `gh pr checks --watch` shows all green
  - **Done when**: PR created, CI passes
  - **If CI fails**:
    1. Read failure details: `gh pr checks`
    2. Fix issues locally
    3. Push fixes: `git push`
    4. Re-verify: `gh pr checks --watch`

- [ ] 4.2 Address code review feedback
  - **Do**: Respond to review comments, make necessary changes, push updates
  - **Files**: tests/e2e/trips.spec.ts, tests/e2e/pages/trips.page.ts
  - **Done when**: All review comments addressed, CI still green
  - **Verify**: `npx playwright test trips.spec.ts && gh pr checks`
  - **Commit**: `fix(trips): address review feedback` (as needed)

## Notes

- **TDD approach**: All implementation driven by failing tests first
- **POC shortcuts taken**: None - full TDD workflow
- **Production TODOs**: None - full implementation in Phase 1
- **Shadow DOM pattern**: Always use `page.locator('ev-trip-planner-panel').locator('#selector')`
- **Dialog handling**: Use `page.on('dialog')` registered before action that triggers dialog
- **Test independence**: Each test creates its own trips, cleanup in test.afterEach()
- **Vehicle ID**: Hardcoded as "Coche2" per requirements (auth.setup.ts config flow)
