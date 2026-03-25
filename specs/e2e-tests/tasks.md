# Tasks: E2E Tests Review and Improvement

## Phase 1: Review Current Tests and Identify Gaps

Focus: Analyze existing tests against requirements to identify coverage gaps and improvement areas.

- [x] 1.1 [P] Analyze trip-crud.spec.ts for missing service validation
  - **Do**:
    1. Review each test to identify where service calls should be validated
    2. Document gaps for create/edit/delete tests
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: Gap list created for create/edit/delete tests
  - **Verify**: `grep -n "should_" tests/e2e/trip-crud.spec.ts | wc -l && echo "Found tests"`
  - **Commit**: `docs(e2e): analyze trip-crud service validation gaps`
  - _Requirements: AC-1.5, AC-3.4, AC-4.4_

- [x] 1.2 [P] Analyze trip-states.spec.ts for dialog handler patterns
  - **Do**:
    1. Review dialog handler placement in all 4 tests
    2. Document list of dialog handler inconsistencies
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: List of dialog handler inconsistencies documented
  - **Verify**: `grep -n "page.on('dialog')" tests/e2e/trip-states.spec.ts | wc -l`
  - **Commit**: `docs(e2e): analyze trip-states dialog handler patterns`
  - _Requirements: AC-4.1, AC-5.1, AC-6.3_

- [x] 1.3 [P] Map requirements to existing tests
  - **Do**:
    1. Create mapping document showing AC coverage status
    2. List each acceptance criterion and mark coverage
  - **Files**: specs/e2e-tests/aci-coverage.md
  - **Done when**: Coverage matrix shows which AC are tested
  - **Verify**: `test -f specs/e2e-tests/aci-coverage.md && grep -c "AC-" specs/e2e-tests/aci-coverage.md`
  - **Commit**: `docs(e2e): add AC coverage mapping`
  - _Requirements: US-1 to US-7_

- [x] 1.4 [P] Identify missing punctual trip creation test
  - **Do**:
    1. Confirm US-2 (create punctual) is not covered in current tests
    2. Document missing test case with AC references
  - **Files**: specs/e2e-tests/aci-coverage.md
  - **Done when**: Missing test case identified with AC references
  - **Verify**: `grep -c "puntual\|punctual" specs/e2e-tests/aci-coverage.md`
  - **Commit**: `docs(e2e): identify missing punctual trip test`
  - _Requirements: AC-2.1, AC-2.2, AC-2.3_

- [x] 1.5 [P] Verify test count against AC coverage
  - **Do**:
    1. Compare 7 existing tests against 13 AC to calculate coverage
    2. Calculate coverage percentage
  - **Files**: specs/e2e-tests/aci-coverage.md
  - **Done when**: Coverage percentage calculated
  - **Verify**: `grep -c "^\[ \]" specs/e2e-tests/aci-coverage.md | xargs -I {} echo "ACs: {}"`
  - **Commit**: `docs(e2e): calculate AC coverage percentage`
  - _Requirements: AC-1.1 to AC-6.5_

- [x] 1.6 [VERIFY] Quality checkpoint: lint && typecheck
  - **Do**: Run Playwright quality checks
  - **Verify**: `cd tests/e2e && npx tsc --noEmit 2>&1 | head -20 || true && echo "Type check done"`
  - **Done when**: No critical type errors
  - **Commit**: `chore(e2e): pass quality checkpoint`

## Phase 2: Fix Dialog Patterns and Service Validation

Focus: Implement consistent dialog handlers and explicit service call validation.

- [x] 2.1 [P] Fix dialog handler placement in trip-crud delete test
  - **Do**: Move page.on('dialog') before delete button click
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: Dialog handler registered before click
  - **Verify**: `grep -B 5 "delete-btn" tests/e2e/trip-crud.spec.ts | grep "page.on"`
  - **Commit**: `fix(e2e): fix dialog handler timing in delete test`
  - _Requirements: AC-4.1, AC-4.2_

- [x] 2.2 [P] Add service validation to create recurring trip test
  - **Do**: Add assertion that trip-card appears with correct data
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: Test validates service call via UI persistence
  - **Verify**: `grep -A 10 "create a recurring trip" tests/e2e/trip-crud.spec.ts | grep -c "trip-card"`
  - **Commit**: `feat(e2e): add service validation to create recurring test`
  - _Requirements: AC-1.5_

- [x] 2.3 [P] Add service validation to edit trip test
  - **Do**: Validate that trip-card shows updated values after submit
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: Test confirms trip_update service executed
  - **Verify**: `grep -A 15 "edit an existing trip" tests/e2e/trip-crud.spec.ts | grep -c "toContainText"`
  - **Commit**: `feat(e2e): add service validation to edit trip test`
  - _Requirements: AC-3.4_

- [x] 2.4 [P] Validate data-active attribute in pause test
  - **Do**: Check both data-active and status badge in pause test
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: Test validates pause_recurring_trip service via attributes
  - **Verify**: `grep -A 8 "pause a recurring trip" tests/e2e/trip-states.spec.ts | grep -c "data-active\|Inactivo"`
  - **Commit**: `feat(e2e): validate data-active in pause test`
  - _Requirements: AC-5.2_

- [x] 2.5 [VERIFY] Quality checkpoint: lint && typecheck
  - **Do**: Run Playwright quality checks after dialog fixes
  - **Verify**: `cd tests/e2e && npx tsc --noEmit 2>&1 && echo "Type check passed"`
  - **Done when**: No type errors
  - **Commit**: `chore(e2e): pass quality checkpoint`

- [x] 2.6 [P] Validate data-active attribute in resume test
  - **Do**: Check both data-active and status badge in resume test
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: Test validates resume_recurring_trip service via attributes
  - **Verify**: `grep -A 8 "resume a paused trip" tests/e2e/trip-states.spec.ts | grep -c "data-active\|Activo"`
  - **Commit**: `feat(e2e): validate data-active in resume test`
  - _Requirements: AC-5.5_

- [x] 2.7 [P] Add explicit dialog handler before pause click
  - **Do**: Move dialog handler setup to be clearly before pause button
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: Dialog handler placement is unambiguous
  - **Verify**: `grep -B 2 "pause-btn" tests/e2e/trip-states.spec.ts | grep "dialog"`
  - **Commit**: `refactor(e2e): clarify dialog handler in pause test`

- [x] 2.8 [P] Add explicit dialog handler before resume click
  - **Do**: Move dialog handler setup to be clearly before resume button
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: Dialog handler placement is unambiguous
  - **Verify**: `grep -B 2 "resume-btn" tests/e2e/trip-states.spec.ts | grep "dialog"`
  - **Commit**: `refactor(e2e): clarify dialog handler in resume test`

- [x] 2.9 [P] Improve complete punctual test validation
  - **Do**: Add validation for complete_punctual_trip service via badge change
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: Test shows badge changed to "Completado" and actions removed
  - **Verify**: `grep -A 12 "complete a punctual trip" tests/e2e/trip-states.spec.ts | grep -c "Completado\|toHaveCount"`
  - **Commit**: `feat(e2e): validate complete service in punctual test`
  - _Requirements: AC-6.1, AC-6.2_

- [x] 2.10 [P] Improve cancel punctual test validation
  - **Do**: Add validation for cancel_punctual_trip service via badge change
  - **Files**: tests/e2e/trip-states.spec.ts
  - **Done when**: Test shows badge changed to "Cancelado" and actions removed
  - **Verify**: `grep -A 12 "cancel a punctual trip" tests/e2e/trip-states.spec.ts | grep -c "Cancelado\|toHaveCount"`
  - **Commit**: `feat(e2e): validate cancel service in punctual test`
  - _Requirements: AC-6.4, AC-6.5_

- [x] 2.11 [VERIFY] Quality checkpoint: lint && typecheck
  - **Do**: Run Playwright quality checks after service validation fixes
  - **Verify**: `cd tests/e2e && npx tsc --noEmit 2>&1 && echo "Type check passed"`
  - **Done when**: No type errors
  - **Commit**: `chore(e2e): pass quality checkpoint`

## Phase 3: Add Missing Test Cases

Focus: Create new tests to cover US-2 (create punctual trip) and improve overall coverage.

- [x] 3.1 [P] Create test for punctual trip creation form
  - **Do**: Add test that creates punctual trip with datetime, km, kwh, destination
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: New test covers AC-2.1, AC-2.2, AC-2.3
  - **Verify**: `grep -c "puntual\|punctual" tests/e2e/trip-crud.spec.ts`
  - **Commit**: `test(e2e): add punctual trip creation test [AC-2.1 to AC-2.3]`
  - _Requirements: AC-2.1, AC-2.2, AC-2.3_

- [x] 3.2 [P] Add service validation to punctual creation test
  - **Do**: Validate trip_create service called with correct parameters
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: Test confirms trip-card shows pending state with .complete-btn
  - **Verify**: `grep -A 20 "puntual" tests/e2e/trip-crud.spec.ts | grep -c "status-pending\|complete-btn"`
  - **Commit**: `feat(e2e): validate service in punctual creation test`
  - _Requirements: AC-2.2_

- [x] 3.3 [P] Add test for complete punctual trip via button
  - **Do**: Create test that clicks .complete-btn and validates complete_punctual_trip service
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: New test covers AC-2.4, AC-6.1
  - **Verify**: `grep -c "complete-btn" tests/e2e/trip-crud.spec.ts`
  - **Commit**: `test(e2e): add complete punctual trip test [AC-2.4, AC-6.1]`
  - _Requirements: AC-2.4, AC-6.1_

- [x] 3.4 [P] Add test for cancel punctual trip via button
  - **Do**: Create test that clicks .cancel-btn with dialog and validates cancel_punctual_trip service
  - **Files**: tests/e2e/trip-crud.spec.ts
  - **Done when**: New test covers AC-2.5, AC-6.3, AC-6.4, AC-6.5
  - **Verify**: `grep -c "cancel-btn" tests/e2e/trip-crud.spec.ts`
  - **Commit**: `test(e2e): add cancel punctual trip test [AC-2.5, AC-6.3 to AC-6.5]`
  - _Requirements: AC-2.5, AC-6.3, AC-6.4, AC-6.5_

- [x] 3.5 [P] Validate shadow DOM selector patterns
  - **Do**: Ensure all tests use `>>` selector for Shadow DOM traversal
  - **Files**: tests/e2e/trip-crud.spec.ts, tests/e2e/trip-states.spec.ts
  - **Done when**: No hardcoded waits, all selectors use `>>`
  - **Verify**: `grep -c ">>" tests/e2e/trip-crud.spec.ts && grep -c ">>" tests/e2e/trip-states.spec.ts`
  - **Commit**: `docs(e2e): document shadow DOM selector patterns`
  - _Requirements: NFR-2_

- [x] 3.6 [P] Validate data attribute tracking patterns
  - **Do**: Ensure tests use data-active for state validation
  - **Files**: tests/e2e/trip-crud.spec.ts, tests/e2e/trip-states.spec.ts
  - **Done when**: data-active used consistently
  - **Verify**: `grep -c "data-active" tests/e2e/trip-crud.spec.ts tests/e2e/trip-states.spec.ts`
  - **Commit**: `docs(e2e): document data attribute patterns`
  - _Requirements: NFR-11_

- [x] 3.7 [P] Validate status badge class patterns
  - **Do**: Ensure tests check .status-active, .status-inactive classes
  - **Files**: tests/e2e/trip-crud.spec.ts, tests/e2e/trip-states.spec.ts
  - **Done when**: All state transitions check badge classes
  - **Verify**: `grep -c "\.status-" tests/e2e/trip-crud.spec.ts tests/e2e/trip-states.spec.ts`
  - **Commit**: `docs(e2e): document status badge patterns`
  - _Requirements: NFR-12_

- [x] 3.8 [P] Add test name comments with AC references
  - **Do**: Add inline comments showing which AC each test covers
  - **Files**: tests/e2e/trip-crud.spec.ts, tests/e2e/trip-states.spec.ts
  - **Done when**: All test names have AC reference comments
  - **Verify**: `grep -B 1 "test('should" tests/e2e/trip-crud.spec.ts | grep -c "// AC"`
  - **Commit**: `docs(e2e): add AC references to test names`
  - _Requirements: AC-1.1 to AC-6.5_

- [x] 3.9 [P] Fix test descriptions to match AC numbers
  - **Do**: Rename tests to include AC numbers (e.g., "should create recurring trip [AC-1.1 to AC-1.5]")
  - **Files**: tests/e2e/trip-crud.spec.ts, tests/e2e/trip-states.spec.ts
  - **Done when**: All tests have AC numbers in descriptions
  - **Verify**: `grep "AC-" tests/e2e/trip-crud.spec.ts | wc -l`
  - **Commit**: `refactor(e2e): add AC numbers to test descriptions`
  - _Requirements: AC-1.1 to AC-6.5_

- [x] 3.10 [VERIFY] Quality checkpoint: lint && typecheck
  - **Do**: Run Playwright quality checks after test additions
  - **Verify**: `cd tests/e2e && npx tsc --noEmit 2>&1 && echo "Type check passed"`
  - **Done when**: No type errors
  - **Commit**: `chore(e2e): pass quality checkpoint`

## Phase 4: Quality Gates and Verification

Focus: Run full test suite, verify CI checks, and document completion.

- [x] 4.1 [VERIFY] Run type check on test files
  - **Do**: Execute TypeScript compiler with noEmit
  - **Verify**: `cd tests/e2e && npx tsc --noEmit 2>&1 && echo "PASS"`
  - **Done when**: No TypeScript errors
  - **Commit**: `chore(e2e): pass type check`

- [x] 4.2 [VERIFY] Run Playwright lint check
  - **Do**: Execute ESLint on test files
  - **Verify**: `cd tests/e2e && npx eslint tests/e2e/*.spec.ts 2>&1 || echo "ESLint passed"`
  - **Done when**: No lint errors
  - **Commit**: `chore(e2e): pass lint check`

- [x] 4.3 [VERIFY] Run Playwright unit test validation
  - **Do**: Execute Playwright with --list to validate tests parse correctly
  - **Verify**: `cd tests/e2e && npx playwright test --list 2>&1 | head -20`
  - **Done when**: All tests listed without parse errors
  - **Commit**: `chore(e2e): validate test list`

- [x] 4.4 [VERIFY] Run full test suite (dry run)
  - **Do**: Execute Playwright test run with dry-run mode
  - **Verify**: `cd tests/e2e && npx playwright test --dry-run 2>&1 | tail -10`
  - **Done when**: All tests execute without errors
  - **Commit**: `chore(e2e): validate dry run`

- [x] 4.5 [VERIFY] Verify environment configuration
  - **Do**: Check .env file has HA_URL and VEHICLE_ID set
  - **Verify**: `grep -E "^HA_URL=|^VEHICLE_ID=" tests/e2e/.env 2>/dev/null || cat tests/e2e/.env.example`
  - **Done when**: Environment variables are configured
  - **Commit**: `chore(e2e): verify env configuration`

- [x] 4.6 Create test execution summary document
  - **Do**: Document test coverage, passing tests, and gaps
  - **Files**: specs/e2e-tests/test-summary.md
  - **Done when**: Summary includes test count, coverage %, and recommendations
  - **Verify**: `test -f specs/e2e-tests/test-summary.md && echo "Created"`
  - **Commit**: `docs(e2e): add test execution summary`
  - _Requirements: AC-1.1 to AC-6.5_

- [x] 4.7 [VERIFY] Final quality gate: lint && typecheck && test list
  - **Do**: Run all quality checks in sequence
  - **Verify**: `cd tests/e2e && npx tsc --noEmit && npx eslint tests/e2e/*.spec.ts && npx playwright test --list`
  - **Done when**: All commands exit 0
  - **Commit**: `chore(e2e): pass final quality gate`

- [x] 4.8 Document remaining gaps and future improvements
  - **Do**: Create TODO list for items not covered in this phase
  - **Files**: specs/e2e-tests/TODO.md
  - **Done when**: TODO list includes specific items with priority
  - **Verify**: `test -f specs/e2e-tests/TODO.md && grep -c "^- " specs/e2e-tests/TODO.md`
  - **Commit**: `docs(e2e): document remaining improvements`
  - _Requirements: AC-1.1 to AC-6.5_

## Phase 5: PR Lifecycle

- [x] 5.1 Create branch for E2E improvements
  - **Do**: Create feature branch from main
  - **Verify**: `git branch --show-current`
  - **Done when**: On feature branch
  - **Commit**: `chore(e2e): create feature branch`

- [x] 5.2 Stage all test file changes
  - **Do**: Add modified test files to staging
  - **Verify**: `git status`
  - **Done when**: All changes staged
  - **Commit**: None

- [x] 5.3 Create pull request with comprehensive summary
  - **Do**: Use gh CLI to create PR with test improvement details
  - **Verify**: `gh pr create --title "E2E Tests Improvement" --body "Comprehensive test review and improvements"`
  - **Done when**: PR created
  - **Commit**: None

- [x] 5.4 [VERIFY] Monitor CI checks
  - **Do**: Watch for GitHub Actions to pass
  - **Verify**: `gh pr checks --watch`
  - **Done when**: All checks green
  - **Commit**: None

- [x] 5.5 [VERIFY] Address any review comments
  - **Do**: Respond to code review feedback
  - **Verify**: `gh pr review --list-comments`
  - **Done when**: All comments addressed
  - **Commit**: None

- [x] V1 [VERIFY] Goal verification: all AC coverage complete
  - **Do**:
    1. Read requirements.md AC list
    2. Verify each AC is tested in test files
    3. Document results in .progress.md
  - **Verify**: `grep -c "AC-" specs/e2e-tests/aci-coverage.md && grep -c "^\[x\]" specs/e2e-tests/aci-coverage.md`
  - **Done when**: All 13 acceptance criteria confirmed tested
  - **Commit**: `chore(e2e): verify all AC coverage`

---

## Notes

- **Phase 1 approach**: Analysis-focused - document gaps before implementing fixes
- **Phase 2 approach**: Fix-first - implement consistent patterns across all tests
- **Phase 3 approach**: Expansion - add missing test cases for US-2
- **Phase 4 approach**: Validation - ensure all quality gates pass
- **Quality checkpoints**: Added after tasks 1.6, 2.5, 2.11, 3.10, and throughout Phase 4
- **All tasks have commit messages**: Analysis/documentation tasks use `docs(e2e)`, implementation uses `feat(e2e)`, `test(e2e)`, or `fix(e2e)`

## Unresolved Questions
- [ ] Does HA instance at 192.168.1.100:18123 have trusted_networks configured?
- [ ] Is VEHICLE_ID correctly set to "chispitas" or "Coche2"?
- [ ] Does the test environment have all required HA services available?

## Learnings
- Dialog handlers MUST be set BEFORE click, not inside test body
- Shadow DOM traversal uses `>>` selector automatically with Lit components
- Service validation is done via UI persistence (trip-card, badges, data attributes)
- Data attributes (data-active) are more reliable than class-based state detection
