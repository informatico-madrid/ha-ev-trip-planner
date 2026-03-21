---

description: "Task list for dashboard CRUD verification feature"
---

# Tasks: Dashboard CRUD Verification

**Input**: Design documents from `/specs/012-dashboard-crud-verify/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Test tasks included - pytest for unit/integration tests, homeassistant-ops skill for API verification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] [VERIFY:TEST|API|BROWSER] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **[VERIFY:...]**: Verification type (see below)
- Include exact file paths in descriptions

### Verification Types

| Tag | When to Use | Verification Method | Available Tools |
|-----|-------------|---------------------|-----------------|
| `[VERIFY:TEST]` | Unit/integration tests (pytest) | Run `pytest tests/ -v` | python-testing-patterns |
| `[VERIFY:API]` | REST API verification (HA entities) | Use homeassistant-ops skill (no hardcoded curl) | homeassistant-ops, homeassistant-skill |
| `[VERIFY:BROWSER]` | Browser automation (Playwright) | Run `npx playwright test` | e2e-testing-patterns |

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Review existing project structure in custom_components/ev_trip_planner/
- [ ] T002 Verify pytest-homeassistant-custom-component is installed and configured
- [ ] T003 [P] Set up test directory structure (tests/ for integration tests)
- [ ] T004 [P] Create conftest.py with HA test fixtures

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core fixes that MUST be complete before ANY user story can work

**CRITICAL**: These are the P001-P004 fixes from spec 011 - they must be fixed first

- [ ] T005 [VERIFY:TEST] Fix KwhTodaySensor state_class from MEASUREMENT to TOTAL_INCREASING in custom_components/ev_trip_planner/sensor.py (FR-001, FR-004)
- [ ] T006 [VERIFY:API] Verify sensor creates without warnings: Use homeassistant-ops skill to check sensor entity state
- [ ] T007 [VERIFY:TEST] Fix NextTripSensor to handle coordinator=None case in custom_components/ev_trip_planner/sensor.py
- [ ] T008 [VERIFY:TEST] Fix EmhassDeferrableLoadSensor to use entry_id instead of vehicle_id in custom_components/ev_trip_planner/sensor.py (FR-004)
- [ ] T009 [VERIFY:API] Verify config entry lookup works: Use homeassistant-ops skill to check config entries
- [ ] T010 [VERIFY:TEST] Implement YAML fallback for trip persistence in custom_components/ev_trip_planner/trip_manager.py (FR-005)
- [ ] T011 [VERIFY:TEST] Write unit tests for trip_manager CRUD operations in tests/test_trip_manager.py
- [ ] T012 [VERIFY:API] Verify sensors are functional without coordinator warnings: check logs for "no coordinator data available"

**Checkpoint**: Foundation ready - all P001-P004 fixes complete, sensors functional

---

## Phase 3: User Story 1 - Complete Vehicle Setup and Full CRUD Dashboard (Priority: P1) 🎯 MVP

**Goal**: Configurar un vehículo eléctrico, acceder a su dashboard y realizar operaciones CRUD completas sobre viajes programados

**Independent Test**:
1. Completar configflow de EV Trip Planner con un vehículo de prueba
2. Verificar que el dashboard aparece en el perfil Lovelace del usuario
3. Crear un viaje desde el dashboard
4. Ver el viaje en la lista de viajes
5. Editar el viaje desde el dashboard
6. Eliminar el viaje desde el dashboard
7. Ejecutar todos los tests y verificar coverage >=80%
8. Verificar 0 errores críticos en logs

**This story includes**: Vehicle setup, dashboard deployment, AND complete CRUD operations on trips through the dashboard UI

### Tests for User Story 1 (REQUIRED) ⚠️

> Write tests FIRST, ensure they FAIL before implementation

- [ ] T020 [P] [US1] [VERIFY:TEST] Add test configflow for vehicle setup in tests/test_config_flow.py (use: python-testing-patterns)
- [ ] T021 [P] [US1] [VERIFY:TEST] Add test dashboard deployment in tests/test_dashboard.py (use: python-testing-patterns)
- [ ] T022 [P] [US1] [VERIFY:TEST] Add test trip CRUD operations in tests/test_trip_crud.py (use: python-testing-patterns)
- [ ] T023 [P] [US1] [VERIFY:BROWSER] Add Playwright E2E test for dashboard UI flows in tests/e2e/test_dashboard_ui.py (use: e2e-testing-patterns)

### Implementation for User Story 1

- [ ] T024 [US1] Implement configflow validation for vehicle data in custom_components/ev_trip_planner/config_flow.py (FR-001)
- [ ] T025 [US1] Add vehicle configuration storage in custom_components/ev_trip_planner/__init__.py
- [ ] T026 [US1] [VERIFY:API] Create vehicle sensors on config entry setup in custom_components/ev_trip_planner/sensor.py (FR-004)
- [ ] T027 [US1] [VERIFY:API] Implement dashboard auto-deployment in custom_components/ev_trip_planner/dashboard.py (FR-002)
- [ ] T028 [US1] [VERIFY:API] Test dashboard visibility: Use homeassistant-ops skill to check Lovelace dashboards
- [ ] T029 [US1] Add error handling for dashboard deployment failures in custom_components/ev_trip_planner/dashboard.py

### Trip CRUD Implementation for User Story 1

- [ ] T030 [US1] [VERIFY:API] Implement trip_create service in custom_components/ev_trip_planner/__init__.py (FR-003, FR-005)
- [ ] T031 [US1] [VERIFY:API] Implement trip_list service in custom_components/ev_trip_planner/__init__.py (FR-003)
- [ ] T032 [US1] [VERIFY:API] Implement trip_update service in custom_components/ev_trip_planner/__init__.py (FR-003)
- [ ] T033 [US1] [VERIFY:API] Implement trip_delete service in custom_components/ev_trip_planner/__init__.py (FR-003)
- [ ] T034 [US1] [VERIFY:API] Create trip sensor entity on trip creation in custom_components/ev_trip_planner/sensor.py (FR-004)
- [ ] T035 [US1] [VERIFY:API] Update trip sensor entity on trip update in custom_components/ev_trip_planner/sensor.py
- [ ] T036 [US1] [VERIFY:API] Remove trip sensor entity on trip deletion in custom_components/ev_trip_planner/sensor.py

### Dashboard UI Implementation for User Story 1

- [ ] T037 [US1] [VERIFY:BROWSER] Implement dashboard create trip form in custom_components/ev_trip_planner/dashboard/dashboard-create.yaml
- [ ] T038 [US1] [VERIFY:BROWSER] Implement dashboard trip list view in custom_components/ev_trip_planner/dashboard/dashboard-list.yaml
- [ ] T039 [US1] [VERIFY:BROWSER] Implement dashboard trip edit form in custom_components/ev_trip_planner/dashboard/dashboard-edit.yaml
- [ ] T040 [US1] [VERIFY:BROWSER] Implement dashboard trip delete confirmation in custom_components/ev_trip_planner/dashboard/dashboard-delete.yaml
- [ ] T041 [US1] [VERIFY:BROWSER] Add JavaScript handlers for CRUD operations in custom_components/ev_trip_planner/dashboard/dashboard.js

**Checkpoint**: User Story 1 complete - vehicle configured, dashboard deployed, full CRUD operations working through UI

**CRITICAL**: This story includes ALL CRUD functionality. No separate stories for create/read/update/delete - all in US1.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Final validation - ALL tests must pass, coverage >=80%, no critical errors

**CRITICAL**: This phase runs ALL tests and verifies everything works end-to-end

- [ ] T047 [P] [VERIFY:TEST] Run complete test suite: `pytest tests/ -v --cov=custom_components/ev_trip_planner`
- [ ] T048 [P] Verify 100% tests passing (0 failures)
- [ ] T049 [P] Verify test coverage >=80% for all CRUD functionality
- [ ] T050 [P] [VERIFY:API] Verify no CRITICAL errors in logs: Use homeassistant-ops skill to check HA logs
- [ ] T051 [P] [VERIFY:API] Verify all services available: Use homeassistant-ops skill to check services
- [ ] T052 [P] [VERIFY:API] Verify dashboard accessible: Use homeassistant-ops skill to check dashboard access
- [ ] T053 [P] [VERIFY:API] Verify all vehicle sensors functional: check each sensor state
- [ ] T054 [P] [VERIFY:API] Full user journey test: create vehicle → create trip → view trips → update trip → delete trip
- [ ] T055 [P] [VERIFY:BROWSER] Playwright E2E test: complete CRUD flow through dashboard UI
- [ ] T056 [P] Update README.md with setup and usage instructions

**CRITICAL SUCCESS CRITERIA**:
- [ ] All tests pass: `pytest tests/ -v` returns 0 failures
- [ ] Coverage >=80%: `pytest --cov-report=term-missing`
- [ ] No critical errors: `grep -i "critical" /config/home-assistant.log` returns empty
- [ ] Full CRUD workflow works through dashboard UI

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P2 → P3 → P3)
- **Polish (Final Phase)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Depends on US2 (create) but independently testable
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Depends on US2 (create) but independently testable

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tasks for User Story 1 together:
Task: "Implement configflow validation for vehicle data in custom_components/ev_trip_planner/config_flow.py"
Task: "Add vehicle configuration storage in custom_components/ev_trip_planner/__init__.py"
Task: "Create vehicle sensors on config entry setup in custom_components/ev_trip_planner/sensor.py"
Task: "Implement dashboard auto-deployment in custom_components/ev_trip_planner/dashboard.py"
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
2. Add User Story 1 → Test independently → Deploy/Demo
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
   - Developer D: User Story 4
   - Developer E: User Story 5
3. Stories complete and integrate independently

---

## Summary

**Total Tasks**: 34 tasks

**Task Distribution**:
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 8 tasks (P001-P004 fixes from spec 011)
- Phase 3 (US1 - Full CRUD): 22 tasks (vehicle setup + dashboard + CRUD operations + tests)
- Phase N (Polish/Final Validation): 10 tasks (all tests, coverage, E2E validation)

**CRITICAL**: All CRUD operations (create, read, update, delete) are included in User Story 1.
No separate stories for CRUD - they are all part of the MVP.

**Independent Test Criteria**:
- US1 complete: Vehicle configured, dashboard deployed, create trip works, view trips works, update trip works, delete trip works, ALL tests pass, coverage >=80%, no critical errors in logs

**Suggested MVP Scope**:
- COMPLETE FEATURE: User Story 1 with ALL CRUD operations through dashboard UI
- This delivers a complete, working integration that users can:
  1. Configure a vehicle
  2. Access the dashboard
  3. Create trips
  4. View trips
  5. Update trips
  6. Delete trips
  7. With all tests passing and coverage >=80%

**Feature Completion Criteria**:
- [ ] All 22 tasks in US1 complete
- [ ] All tests pass: `pytest tests/ -v` returns 0 failures
- [ ] Coverage >=80%: `pytest --cov-report=term-missing`
- [ ] No critical errors: `grep -i "critical" /config/home-assistant.log` returns empty
- [ ] Full CRUD workflow works through dashboard UI (Playwright E2E test passes)

**Verification Commands**:
- Unit tests: `pytest tests/ -v --cov=custom_components/ev_trip_planner`
- Test results: Check for 0 failures
- Coverage: `pytest --cov-report=term-missing | grep "TOTAL"`
- API verification: Use homeassistant-ops skill to check sensor entities
- Dashboard check: Use homeassistant-ops skill to check Lovelace dashboards
- Services check: Use homeassistant-ops skill to check services
- Log check: `grep -i "critical\|error" /config/home-assistant.log | grep -i "ev_trip_planner"`
- E2E test: `npx playwright test tests/e2e/`
