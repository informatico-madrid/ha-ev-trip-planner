---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] [VERIFY:TEST|API|BROWSER] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **[VERIFY:...]**: Verification type (see below)
- Include exact file paths in descriptions

### Verification Types

**IMPORTANT**: Before assigning verification types, consult the "Available Tools for Verification" section in plan.md to see which skills/MCPs are available in this project.

| Tag | When to Use | Verification Method | Available MCP/SKILL |
|-----|-------------|---------------------|---------------------|
| `[VERIFY:TEST]` | pytest unit/integration tests | Run `pytest tests/ -v` | `[MCP_TESTING]` or `[SKILL_TESTING]` |
| `[VERIFY:E2E]` | End-to-end validation of user story | Agent executes E2E test sequence | `[MCP_E2E]` or `[SKILL_E2E]` |
| `[VERIFY:BROWSER]` | Integrated verification of ALL features | Agent navigates autonomously with MCP at END only | `[MCP_BROWSER]` or `[SKILL_BROWSER]` |
| `[VERIFY:API]` | HA REST API verification | Use HA API tools | `[MCP_API]` or `[SKILL_API]` |
| `[VERIFY:CONFIG]` | HA YAML configuration | Use HA config tools | `[MCP_CONFIG]` or `[SKILL_CONFIG]` |

**Task Assignment Rules**:
- **TDD**: Write tests FIRST that fail, then implement
- **E2E Tests**: Add at the END of each user story/fase to validate complete story
- **VERIFY:BROWSER**: Use ONCE at the end (task T999) for integrated verification - DO NOT distribute across individual user stories
- Only add skill/MCP reference if you find relevant tools for that specific verification type in plan.md - otherwise omit the reference

### VERIFY:API - Home Assistant API Verification Steps

When a task has `[VERIFY:API]`, use the homeassistant-ops skill to verify:

**IMPORTANT**: Replace the placeholders below with actual working endpoints from the project before generating tasks.

1. **Check API connectivity**: `[API_ENDPOINT_CONNECTIVITY]` - expect 200
2. **List all entities**: `[API_ENDPOINT_STATES]`
3. **Get specific entity**: `[API_ENDPOINT_ENTITY]` - use entity_id from data-model.md
4. **List services**: `[API_ENDPOINT_SERVICES]`
5. **Check config**: `[API_ENDPOINT_CONFIG]`
6. **Call a service**: `[API_ENDPOINT_SERVICE_CALL]` - use domain/service from services.yaml

**Required**: Set `HA_URL` and `HA_TOKEN` environment variables before running.

**Note**: The agent must verify which endpoints are actually working in the HA instance before substituting these placeholders.

### VERIFY:BROWSER - Integrated Verification (T999 Only)

**IMPORTANT**: This verification type is used ONLY ONCE at the end of ALL tasks (task T999) for integrated verification of the COMPLETE feature. Do NOT distribute across individual user stories.

When task T999 has `[VERIFY:BROWSER]`, the agent must:

1. **Preparation**: Review all implemented features from spec.md
2. **Optimize test sequence**: Create optimal order of verification steps (e.g., create multiple test objects upfront to reuse for testing multiple features)
3. **Execute integrated verification**: Navigate through ALL user stories in logical order
4. **Edge cases**: Test boundary conditions and error scenarios
5. **Document issues**: If any feature fails, document which task needs fixing

**Example optimized verification flow**:
```
FASE 0: Preparación → FASE 1: Crear integración → FASE 2-15: Verificar cada US → FASE FINAL: CRUD completo
```

**Key principle**: Create several test objects/entities upfront, then use them to test MULTIPLE features efficiently. Don't test one-by-one; maximize coverage with minimum steps.

**Debug Commands** (use when tests fail):

| Command | Description |
|---------|-------------|
| `npx playwright test --debug` | Run with Playwright Inspector (pauses on each step) |
| `npx playwright test --trace on` | Record trace for all tests |
| `npx playwright test --trace retain-on-failure` | Keep trace only on failures |
| `npx playwright show-trace <trace-file>` | View recorded trace |
| `npx playwright test --headed` | Run visible browser (not headless) |
| `npx playwright test --ui` | Interactive UI mode |
| `npx playwright test --shard 1/3` | Run specific shard of tests |

**Key difference from [VERIFY:TEST]**: `[VERIFY:BROWSER]` at T999 validates ALL user stories together as an integrated system, not individual stories in isolation.

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 [VERIFY:TEST] Setup database schema and migrations framework (use: `[SKILL_TESTING]`)
- [ ] T005 [P] [VERIFY:TEST] Implement authentication/authorization framework (use: `[SKILL_TESTING]`)
- [ ] T006 [P] [VERIFY:API] Setup API routing and middleware structure (use: `[SKILL_API]`)
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure
- [ ] T009 [VERIFY:API] Setup environment configuration management (use: `[SKILL_CONFIG]`)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (TDD + E2E) ⚠️

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] [VERIFY:TEST] Contract test for [endpoint] in tests/contract/test_[name].py (use: python-testing-patterns)
- [ ] T011 [P] [US1] [VERIFY:TEST] Integration test for [user journey] in tests/integration/test_[name].py (use: python-testing-patterns)

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T013 [P] [US1] Create [Entity2] model in src/models/[entity2].py
- [ ] T014 [US1] [VERIFY:API] Implement [Service] in src/services/[service].py (depends on T012, T013)
- [ ] T015 [US1] [VERIFY:API] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T016 [US1] Add validation and error handling
- [ ] T017 [US1] [VERIFY:API] Add logging for user story 1 operations

### E2E Validation for User Story 1 (at end of US)

- [ ] T018 [US1] [VERIFY:E2E] Execute E2E test sequence to validate complete user story 1 (use: e2e-testing-patterns)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (TDD + E2E) ⚠️

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T020 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T021 [US2] Implement [Service] in src/services/[service].py
- [ ] T022 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T023 [US2] Integrate with User Story 1 components (if needed)

### E2E Validation for User Story 2 (at end of US)

- [ ] T024 [US2] [VERIFY:E2E] Execute E2E test sequence to validate complete user story 2

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (TDD + E2E) ⚠️

- [ ] T025 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T026 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T027 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T028 [US3] Implement [Service] in src/services/[service].py
- [ ] T029 [US3] Implement [endpoint/feature] in src/[location]/[file].py

### E2E Validation for User Story 3 (at end of US)

- [ ] T030 [US3] [VERIFY:E2E] Execute E2E test sequence to validate complete user story 3

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern: Tests → Implementation → E2E Validation]

---

## Phase Final: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX Optimize performance across all features
- [ ] TXXX Add comprehensive error handling
- [ ] TXXX Implement logging and monitoring
- [ ] TXXX Code review and refactoring
- [ ] TXXX Security hardening

---

## Phase Final: Update Documentation

**Purpose**: After everything is verified working, update documentation

- [ ] TXXX Update README.md with new features
- [ ] TXXX Document API changes in API docs
- [ ] TXXX Update configuration examples
- [ ] TXXX Add usage examples and tutorials

---

## Phase Final: Integrated Verification (T999)

- [ ] T999 [VERIFY:BROWSER] Comprehensive integrated verification of ALL features

**Objective**: Validate the COMPLETE feature as an integrated system, not individual components.

**Verification Strategy**:
1. Create optimal test data upfront (multiple entities/objects to reuse)
2. Verify all user stories in logical order
3. Test edge cases and boundary conditions
4. Document any issues found and which tasks need fixing

**Expected Outcome**: All features working together seamlessly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete
- **Documentation (Final Phase)**: Depends on all features verified working
- **Integrated Verification (T999)**: Final checkpoint before completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- [VERIFY:TEST] = pytest unit/integration tests (use `[SKILL_TESTING]`)
- [VERIFY:API] = Home Assistant REST API verification (use `[SKILL_API]`)
- [VERIFY:BROWSER] = Playwright autonomous browser navigation - agent must find the path to complete goal (use `[SKILL_BROWSER]`)
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
