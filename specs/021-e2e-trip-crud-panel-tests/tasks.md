# Tasks: E2E Tests for Trip CRUD Panel

## Phase 1: Make It Work (POC)

**Focus**: Implement browser-based tests for critical CRUD operations.

### Task 1.1: Setup Test Infrastructure
- [x] **Do**: Verify Playwright configuration and test setup
- [x] **Files**: `tests/e2e/playwright.config.ts`
- [x] **Done when**: Playwright can run tests against HA instance
- [x] **Verify**: `npx playwright --version` shows v1.58.2
- [x] **Commit**: `test(e2e): setup Playwright infrastructure for panel tests`

### Task 1.2: Implement Panel Loading Test
- [x] **Do**: Create test that verifies panel loads and extracts vehicle ID
- [x] **Files**: `tests/e2e/test-panel-loading.spec.ts`
- [x] **Done when**: Test passes at URL `/ev-trip-planner-{vehicle_id}`
- [x] **Verify**: `npx playwright test test-panel-loading.spec.ts`
- [x] **Commit**: `test(e2e): add panel loading test`

### Task 1.3: Implement Trip List Loading Test
- [x] **Do**: Create test that verifies trips load from service
- [x] **Files**: `tests/e2e/test-trip-list.spec.ts`
- [x] **Done when**: Test verifies trips section displays correctly
- [x] **Verify**: `npx playwright test test-trip-list.spec.ts`
- [x] **Commit**: `test(e2e): add trip list loading test`

### Task 1.4: Implement Create Trip Test
- [x] **Do**: Create test that fills form and creates a trip
- [x] **Files**: `tests/e2e/test-create-trip.spec.ts`
- [x] **Done when**: Test verifies trip creation workflow
- [x] **Verify**: `npx playwright test test-create-trip.spec.ts`
- [x] **Commit**: `test(e2e): add create trip test`

### Task 1.5: Implement Edit Trip Test
- [x] **Do**: Create test that edits an existing trip
- [x] **Files**: `tests/e2e/test-edit-trip.spec.ts`
- [x] **Done when**: Test verifies form pre-fills and updates work
- [x] **Verify**: `npx playwright test test-edit-trip.spec.ts`
- [x] **Commit**: `test(e2e): add edit trip test`

### Task 1.6: Implement Delete Trip Test
- [x] **Do**: Create test that deletes a trip with confirmation
- [x] **Files**: `tests/e2e/test-delete-trip.spec.ts`
- [x] **Done when**: Test verifies confirmation dialog and deletion
- [x] **Verify**: `npx playwright test test-delete-trip.spec.ts`
- [x] **Commit**: `test(e2e): add delete trip test`

## Phase 2: Refactoring

After POC validated, clean up test code and add error handling.

### Task 2.1: Create Test Base Class
- [x] **Do**: Extract common test setup into base class
- [x] **Files**: `tests/e2e/test-base.spec.ts`
- [x] **Done when**: All tests extend base class for consistency
- [x] **Verify**: Code structure is clean and maintainable
- [x] **Commit**: `refactor(e2e): create test base class`

### Task 2.2: Add Error Handling
- [x] **Do**: Add try/catch with meaningful error messages
- [x] **Files**: All test files
- [x] **Done when**: Test failures show clear error messages
- [x] **Verify**: `npx playwright test --reporter=line`
- [x] **Commit**: `refactor(e2e): add error handling to tests`

### Task 2.3: Add Test Hooks
- [x] **Do**: Add beforeEach/afterEach hooks for setup/cleanup
- [x] **Files**: All test files
- [x] **Done when**: Tests have consistent setup and teardown
- [x] **Verify**: No test state leakage between tests
- [x] **Commit**: `refactor(e2e): add test hooks`

## Phase 3: Testing

Add comprehensive tests for remaining CRUD operations.

### Task 3.1: Implement Pause/Resume Test
- [x] **Do**: Create test for pausing and resuming recurring trips
- [x] **Files**: `tests/e2e/test-pause-resume.spec.ts`
- [x] **Done when**: Test verifies pause and resume workflows
- [x] **Verify**: `npx playwright test test-pause-resume.spec.ts`
- [x] **Commit**: `test(e2e): add pause/resume test`

### Task 3.2: Implement Complete/Cancel Test
- [x] **Do**: Create test for completing and canceling punctual trips
- [x] **Files**: `tests/e2e/test-complete-cancel.spec.ts`
- [x] **Done when**: Test verifies complete and cancel workflows
- [x] **Verify**: `npx playwright test test-complete-cancel.spec.ts`
- [x] **Commit**: `test(e2e): add complete/cancel test`

### Task 3.3: Add Integration Tests
- [x] **Do**: Create tests that exercise multiple CRUD operations in sequence
- [x] **Files**: `tests/e2e/test-integration.spec.ts`
- [x] **Done when**: Tests verify full user workflows
- [x] **Verify**: `npx playwright test test-integration.spec.ts`
- [x] **Commit**: `test(e2e): add integration tests`

## Phase 4: Quality Gates

Verify all quality gates pass before PR.

### Task 4.1: Test All Browsers
- [x] **Do**: Run tests in Chrome, Firefox, Safari
- [x] **Verify**: `npx playwright test --project=chromium`
- [x] **Verify**: `npx playwright test --project=firefox`
- [x] **Verify**: `npx playwright test --project=webkit`
- [x] **Done when**: All tests pass in all browsers
- [x] **Commit**: `test(e2e): verify cross-browser compatibility`

### Task 4.2: Performance Testing
- [x] **Do**: Measure test execution time
- [x] **Verify**: Total test time < 5 minutes
- [x] **Done when**: Performance requirements met
- [x] **Commit**: `test(e2e): verify performance requirements`

### Task 4.3: Create PR
- [ ] **Do**: Create PR and verify CI passes
- [ ] **Verify**: `gh pr create --title "test(e2e): add comprehensive panel CRUD tests"`
- [ ] **Verify**: `gh pr checks --watch`
- [ ] **Done when**: All CI checks pass
- [ ] **Commit**: None

## Summary

**Total Tasks**: 13 tasks across 5 phases

**Completed**: 12/13 tasks

**Remaining Effort**: Final PR creation

**Priority**: High (blocks production deployment)

**Dependencies**:
- Task 1.1 must complete before all other tests
- Task 1.2-1.6 can run in parallel
- Task 2.1 must complete before Task 2.2-2.3
- Task 3.1-3.3 can run in parallel

**Rollback Plan**: If tests fail, check HA instance, integration installation, and test data setup.
