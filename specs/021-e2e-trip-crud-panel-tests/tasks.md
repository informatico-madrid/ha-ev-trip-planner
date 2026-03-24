# Tasks: E2E Tests for Trip CRUD Panel

## Phase 1: Make It Work (POC)

**Focus**: Implement browser-based tests for critical CRUD operations.

### Task 1.1: Setup Test Infrastructure
- **Do**: Verify Playwright configuration and test setup
- **Files**: `tests/e2e/playwright.config.ts`
- **Done when**: Playwright can run tests against HA instance
- **Verify**: `npx playwright --version` shows v1.58.2
- **Commit**: `test(e2e): setup Playwright infrastructure for panel tests`

### Task 1.2: Implement Panel Loading Test
- **Do**: Create test that verifies panel loads and extracts vehicle ID
- **Files**: `tests/e2e/test-panel-loading.spec.ts`
- **Done when**: Test passes at URL `/ev-trip-planner-{vehicle_id}`
- **Verify**: `npx playwright test test-panel-loading.spec.ts`
- **Commit**: `test(e2e): add panel loading test`

### Task 1.3: Implement Trip List Loading Test
- **Do**: Create test that verifies trips load from service
- **Files**: `tests/e2e/test-trip-list.spec.ts`
- **Done when**: Test verifies trips section displays correctly
- **Verify**: `npx playwright test test-trip-list.spec.ts`
- **Commit**: `test(e2e): add trip list loading test`

### Task 1.4: Implement Create Trip Test
- **Do**: Create test that fills form and creates a trip
- **Files**: `tests/e2e/test-create-trip.spec.ts`
- **Done when**: Test verifies trip creation workflow
- **Verify**: `npx playwright test test-create-trip.spec.ts`
- **Commit**: `test(e2e): add create trip test`

### Task 1.5: Implement Edit Trip Test
- **Do**: Create test that edits an existing trip
- **Files**: `tests/e2e/test-edit-trip.spec.ts`
- **Done when**: Test verifies form pre-fills and updates work
- **Verify**: `npx playwright test test-edit-trip.spec.ts`
- **Commit**: `test(e2e): add edit trip test`

### Task 1.6: Implement Delete Trip Test
- **Do**: Create test that deletes a trip with confirmation
- **Files**: `tests/e2e/test-delete-trip.spec.ts`
- **Done when**: Test verifies confirmation dialog and deletion
- **Verify**: `npx playwright test test-delete-trip.spec.ts`
- **Commit**: `test(e2e): add delete trip test`

## Phase 2: Refactoring

After POC validated, clean up test code and add error handling.

### Task 2.1: Create Test Base Class
- **Do**: Extract common test setup into base class
- **Files**: `tests/e2e/test-base.spec.ts`
- **Done when**: All tests extend base class for consistency
- **Verify**: Code structure is clean and maintainable
- **Commit**: `refactor(e2e): create test base class`

### Task 2.2: Add Error Handling
- **Do**: Add try/catch with meaningful error messages
- **Files**: All test files
- **Done when**: Test failures show clear error messages
- **Verify**: `npx playwright test --reporter=line`
- **Commit**: `refactor(e2e): add error handling to tests`

### Task 2.3: Add Test Hooks
- **Do**: Add beforeEach/afterEach hooks for setup/cleanup
- **Files**: All test files
- **Done when**: Tests have consistent setup and teardown
- **Verify**: No test state leakage between tests
- **Commit**: `refactor(e2e): add test hooks`

## Phase 3: Testing

Add comprehensive tests for remaining CRUD operations.

### Task 3.1: Implement Pause/Resume Test
- **Do**: Create test for pausing and resuming recurring trips
- **Files**: `tests/e2e/test-pause-resume.spec.ts`
- **Done when**: Test verifies pause and resume workflows
- **Verify**: `npx playwright test test-pause-resume.spec.ts`
- **Commit**: `test(e2e): add pause/resume test`

### Task 3.2: Implement Complete/Cancel Test
- **Do**: Create test for completing and canceling punctual trips
- **Files**: `tests/e2e/test-complete-cancel.spec.ts`
- **Done when**: Test verifies complete and cancel workflows
- **Verify**: `npx playwright test test-complete-cancel.spec.ts`
- **Commit**: `test(e2e): add complete/cancel test`

### Task 3.3: Add Integration Tests
- **Do**: Create tests that exercise multiple CRUD operations in sequence
- **Files**: `tests/e2e/test-integration.spec.ts`
- **Done when**: Tests verify full user workflows
- **Verify**: `npx playwright test test-integration.spec.ts`
- **Commit**: `test(e2e): add integration tests`

## Phase 4: Quality Gates

Verify all quality gates pass before PR.

### Task 4.1: Test All Browsers
- **Do**: Run tests in Chrome, Firefox, Safari
- **Verify**: `npx playwright test --project=chromium`
- **Verify**: `npx playwright test --project=firefox`
- **Verify**: `npx playwright test --project=webkit`
- **Done when**: All tests pass in all browsers
- **Commit**: `test(e2e): verify cross-browser compatibility`

### Task 4.2: Performance Testing
- **Do**: Measure test execution time
- **Verify**: Total test time < 5 minutes
- **Done when**: Performance requirements met
- **Commit**: `test(e2e): verify performance requirements`

### Task 4.3: Create PR
- **Do**: Create PR and verify CI passes
- **Verify**: `gh pr create --title "test(e2e): add comprehensive panel CRUD tests"`
- **Verify**: `gh pr checks --watch`
- **Done when**: All CI checks pass
- **Commit**: None

## Phase 5: PR Lifecycle

Continuous validation until all completion criteria met.

### Task 5.1: Address Review Comments
- **Do**: Review PR comments, make requested changes
- **Done when**: All comments addressed
- **Commit**: Depends on feedback

### Task 5.2: Final Validation
- **Do**: Verify all acceptance criteria met
- **Verify**: All AC-1.* through AC-7.* satisfied
- **Done when**: All criteria verified
- **Commit**: None

### Task 5.3: E2E Verification
- **Do**: Run tests against real HA instance
- **Verify**: `HA_URL=http://ha:8123 npx playwright test`
- **Done when**: All tests pass on real HA
- **Commit**: None

## Summary

**Total Tasks**: 13 tasks across 5 phases

**Estimated Effort**: 4-6 hours

**Priority**: High (blocks production deployment)

**Dependencies**:
- Task 1.1 must complete before all other tests
- Task 1.2-1.6 can run in parallel
- Task 2.1 must complete before Task 2.2-2.3
- Task 3.1-3.3 can run in parallel

**Rollback Plan**: If tests fail, check HA instance, integration installation, and test data setup.
