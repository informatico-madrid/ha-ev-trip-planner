---

description: "Task list for E2E Playwright Testing feature"
---

# Tasks: E2E Playwright Testing para Panel Nativo de Home Assistant

**Input**: Design documents from `/specs/018-e2e-playwright-testing/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: This feature IS a test suite - the tasks implement Playwright browser automation tests that verify the native panel creation workflow.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] [VERIFY:TEST|API|BROWSER] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **[VERIFY:...]**: Verification type (see below)
- Include exact file paths in descriptions

### Verification Types

**IMPORTANT**: Before assigning verification types, consult the plan's "Available Tools for Verification" section to see which skills/MCPs are installed.

| Tag | When to Use | Verification Method | Available Tools |
|-----|-------------|---------------------|----------------|
| `[VERIFY:TEST]` | Unit/integration tests (pytest) | Run `pytest tests/ -v` | python-testing-patterns, e2e-testing-patterns |
| `[VERIFY:API]` | REST API verification (HA entities) | Use homeassistant-ops skill (no hardcoded curl) | homeassistant-ops, homeassistant-skill |
| `[VERIFY:BROWSER]` | Browser automation (Playwright) | Run `npx playwright test` | e2e-testing-patterns |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for Playwright E2E testing

- [ ] T001 [P] Verify Node.js 18+ and npm are installed
- [ ] T002 [P] Install Playwright dependencies: `npm install` and `npx playwright install` [use: e2e-testing-patterns]
- [ ] T003 Create .env file with HA credentials (HA_URL, HA_USERNAME, HA_TOKEN) per quickstart.md
- [ ] T004 Verify playwright.config.js exists and is properly configured [use: e2e-testing-patterns]
- [ ] T005 [P] Create tests/e2e/ directory structure with pages/ subdirectory

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] [VERIFY:BROWSER] Create base test infrastructure in tests/e2e/base.spec.js (use: e2e-testing-patterns)
- [ ] T007 [P] [VERIFY:BROWSER] Create HA Login page object in tests/e2e/pages/ha-login.page.ts (use: e2e-testing-patterns)
- [ ] T008 [P] [VERIFY:BROWSER] Create HA Integrations page object in tests/e2e/pages/ha-integrations.page.ts (use: e2e-testing-patterns)
- [ ] T009 [P] [VERIFY:BROWSER] Create EV Trip Planner config flow page object in tests/e2e/pages/ev-trip-planner.page.ts (use: e2e-testing-patterns)
- [ ] T010 [VERIFY:BROWSER] Setup console log and error capture in tests/e2e/utils/capture-logs.js (use: e2e-testing-patterns)
- [ ] T011 Setup screenshot capture utility for debugging failures
- [ ] T012 [VERIFY:API] Verify Home Assistant is accessible via API (use: homeassistant-ops)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Crear vehículo mediante config flow con Playwright (Priority: P1) 🎯 MVP

**Goal**: Navigate to Home Assistant with Playwright, login, navigate to integrations, add EV Trip Planner, and complete the config flow to create a vehicle

**Independent Test**: Execute the Playwright test and verify the config flow completes without errors, creating a vehicle entry in Home Assistant

### Implementation for User Story 1

- [ ] T013 [P] [US1] [VERIFY:BROWSER] Implement navigation to HA login page in tests/e2e/test-config-flow.spec.js (use: e2e-testing-patterns)
- [ ] T014 [P] [US1] [VERIFY:BROWSER] Implement login flow with credentials in tests/e2e/test-config-flow.spec.js (use: e2e-testing-patterns)
- [ ] T015 [US1] [VERIFY:BROWSER] Implement navigation to /config/integrations in tests/e2e/test-config-flow.spec.js (use: e2e-testing-patterns)
- [ ] T016 [US1] [VERIFY:BROWSER] Implement adding EV Trip Planner integration in tests/e2e/test-config-flow.spec.js (use: e2e-testing-patterns)
- [ ] T017 [US1] [VERIFY:BROWSER] Implement config flow completion with vehicle data in tests/e2e/test-config-flow.spec.js (use: e2e-testing-patterns)
- [ ] T018 [US1] [VERIFY:API] Verify vehicle entity was created in HA after config flow (use: homeassistant-ops)

**Checkpoint**: At this point, User Story 1 should be fully functional - vehicle can be created via Playwright automation

---

## Phase 4: User Story 2 - Verificar panel nativo accesible con Playwright (Priority: P1)

**Goal**: Verify that the native panel appears in the Home Assistant sidebar and is accessible

**Independent Test**: Execute the Playwright test and verify the panel is visible in the sidebar and loads without errors

### Implementation for User Story 2

- [ ] T019 [P] [US2] [VERIFY:BROWSER] Implement sidebar panel verification in tests/e2e/test-native-panel.spec.js (use: e2e-testing-patterns)
- [ ] T020 [P] [US2] [VERIFY:BROWSER] Implement panel URL navigation in tests/e2e/test-native-panel.spec.js (use: e2e-testing-patterns)
- [ ] T021 [US2] [VERIFY:BROWSER] Implement panel content verification in tests/e2e/test-native-panel.spec.js (use: e2e-testing-patterns)
- [ ] T022 [US2] [VERIFY:API] Verify panel is registered via HA API (use: homeassistant-ops)
- [ ] T023 [US2] [VERIFY:API] Verify all expected entities exist for the vehicle via HA API (use: homeassistant-ops)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - vehicle creation and panel verification

---

## Phase 5: User Story 3 - Debugging y corrección iterativa (Priority: P2)

**Goal**: Add comprehensive logging, error capture, and retry mechanisms for iterative debugging

**Independent Test**: Execute tests with failures and verify detailed logs/screenshots are captured for debugging

### Implementation for User Story 3

- [ ] T024 [P] [US3] [VERIFY:BROWSER] Implement comprehensive console log capture in tests/e2e/utils/capture-logs.js (use: e2e-testing-patterns)
- [ ] T025 [P] [US3] [VERIFY:BROWSER] Implement page error capture with stack traces in tests/e2e/utils/capture-logs.js (use: e2e-testing-patterns)
- [ ] T026 [US3] [VERIFY:BROWSER] Implement screenshot capture on test failure in tests/e2e/test-native-panel.spec.js (use: e2e-testing-patterns)
- [ ] T027 [US3] [VERIFY:BROWSER] Implement retry mechanism for flaky steps in config flow (use: e2e-testing-patterns)
- [ ] T028 [US3] [VERIFY:API] Add HA logs verification when panel fails (use: homeassistant-ops)

**Checkpoint**: All user stories should now be independently functional with proper debugging capabilities

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T029 [P] Update README.md with test execution instructions
- [ ] T030 Add test documentation in tests/e2e/README.md
- [ ] T031 [P] Run quickstart.md validation - verify all tests execute successfully
- [ ] T032 Clean up and organize test files
- [ ] T033 Add CI configuration for automated test execution (optional)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Should be independently testable from US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Adds debugging on top of US1 and US2

### Within Each User Story

- Page Objects before tests
- Each test step builds on previous steps
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- User Story 1 and 2 can run in parallel after Foundational
- Page Objects (T007, T008, T009) can be created in parallel

---

## Parallel Example: User Story Implementation

```bash
# Launch foundational page objects in parallel:
Task: "Create HA Login page object in tests/e2e/pages/ha-login.page.ts"
Task: "Create HA Integrations page object in tests/e2e/pages/ha-integrations.page.ts"
Task: "Create EV Trip Planner config flow page object in tests/e2e/pages/ev-trip-planner.page.ts"

# Launch user stories in parallel after foundation:
Task: "User Story 1 - Crear vehículo mediante config flow"
Task: "User Story 2 - Verificar panel nativo accesible"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently - can create a vehicle via Playwright
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - can create vehicles!)
3. Add User Story 2 → Test independently → Deploy/Demo (panel verification works!)
4. Add User Story 3 → Test independently → Deploy/Demo (full debugging capability)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (config flow automation)
   - Developer B: User Story 2 (panel verification)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- [VERIFY:TEST] = unit/integration tests (pytest) - NOT USED in this feature
- [VERIFY:API] = REST API verification via homeassistant-ops skill
- [VERIFY:BROWSER] = Playwright E2E tests via e2e-testing-patterns skill
- Each user story should be independently completable and testable
- This feature IS the test suite - tests are the implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Summary

- **Total Tasks**: 33
- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 7 tasks
- **Phase 3 (US1 - Config Flow)**: 6 tasks
- **Phase 4 (US2 - Panel Verification)**: 5 tasks
- **Phase 5 (US3 - Debugging)**: 5 tasks
- **Phase 6 (Polish)**: 5 tasks
- **Parallel Opportunities**: 12 tasks marked [P]
- **MVP Scope**: User Story 1 (T013-T018) - ability to create vehicles via Playwright

## Extension Hooks

No extension hooks registered - `.specify/extensions.yml` does not exist in project root.
