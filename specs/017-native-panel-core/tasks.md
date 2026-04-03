# Tasks: Panel de Control Nativo Integrado en Home Assistant Core

**Input**: Design documents from `/specs/017-native-panel-core/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

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
| `[VERIFY:API]` | REST API verification (HA entities) | Use homeassistant-ops skill (no hardcoded curl) | homeassistant-ops, homeassistant-skill |

**Task Assignment Rule**: For each task, determine which verification type applies, then select the most appropriate tool from the available skills/MCPs listed in plan.md.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 [VERIFY:BROWSER] Create project structure per implementation plan in specs/017-native-panel-core/
- [ ] T002 [VERIFY:BROWSER] Initialize JavaScript panel component with ES6 modules
- [ ] T003 [P] [VERIFY:BROWSER] Configure CSS styles for panel in custom_components/ev_trip_planner/frontend/panel.css
- [ ] T004 [P] [VERIFY:BROWSER] Set up package.json for panel dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [VERIFY:TEST] Create mock setup utilities for testing panel.py in tests/test_panel.py
- [ ] [P] T006 [VERIFY:TEST] Implement panel registry manager in custom_components/ev_trip_planner/panel.py
- [ ] [P] T007 [VERIFY:API] Set up frontend static path registration in __init__.py
- [ ] [P] T008 [VERIFY:API] Create vehicle configuration handler for panel registration
- [ ] T009 [VERIFY:API] Set up error handling and logging infrastructure for panel registration

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Creación automática del panel al configurar vehículo (Priority: P1) 🎯 MVP

**Goal**: Al configurar un vehículo desde el config flow, se crea automáticamente un panel de control en el sidebar de Home Assistant

**Independent Test**:
- [ ] Configurar un nuevo vehículo mediante el config flow
- [ ] Verificar que aparece un nuevo panel en el sidebar de Home Assistant
- [ ] El panel debe mostrar información del vehículo sin errores

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] [VERIFY:TEST] Test panel registration in tests/test_panel_registration.py (use: python-testing-patterns)

### Implementation for User Story 1

- [ ] T012 [P] [US1] [VERIFY:BROWSER] Implement panel registration in config_flow.py when config entry is added
- [ ] T013 [P] [US1] [VERIFY:BROWSER] Create frontend URL path generator for vehicle-specific panels in custom_components/ev_trip_planner/panel.py
- [ ] T014 [US1] [VERIFY:BROWSER] Register panel using panel_custom.async_register_panel in custom_components/ev_trip_planner/panel.py
- [ ] T015 [US1] [VERIFY:BROWSER] Add sidebar_title and sidebar_icon configuration for EV Trip Planner panel
- [ ] T016 [US1] [VERIFY:BROWSER] Add error handling for panel registration failures
- [ ] T017 [US1] [VERIFY:API] Add logging for panel registration events in custom_components/ev_trip_planner/panel.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Ver información del vehículo en el panel nativo (Priority: P1)

**Goal**: Mostrar el estado actual del vehículo (SOC, autonomía, carga) en el panel nativo

**Independent Test**:
- [ ] Acceder al panel desde el sidebar
- [ ] Verificar que se muestra el estado actual del vehículo
- [ ] Los datos deben coincidir con los sensores de Home Assistant

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T018 [P] [US2] [VERIFY:TEST] Test vehicle state display in tests/test_vehicle_state_display.py (use: python-testing-patterns)

### Implementation for User Story 2

- [ ] T020 [P] [US2] [VERIFY:BROWSER] Create JavaScript API client in custom_components/ev_trip_planner/frontend/panel.js for HA REST API
- [ ] T021 [P] [US2] [VERIFY:BROWSER] Fetch vehicle state from Home Assistant sensors in panel.js
- [ ] T022 [US2] [VERIFY:BROWSER] Display SOC percentage and battery status in custom_components/ev_trip_planner/frontend/panel.js
- [ ] T023 [US2] [VERIFY:BROWSER] Display estimated autonomy in custom_components/ev_trip_planner/frontend/panel.js
- [ ] T024 [US2] [VERIFY:BROWSER] Display charging status with visual indicators in custom_components/ev_trip_planner/frontend/panel.js
- [ ] T025 [US2] [VERIFY:BROWSER] Implement real-time updates using HA WebSocket subscription in panel.js

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Gestionar viajes desde el panel nativo (Priority: P1)

**Goal**: Crear, editar y eliminar viajes desde el panel nativo sin depender de Lovelace

**Independent Test**:
- [ ] Crear un nuevo viaje desde el panel
- [ ] Editar un viaje existente
- [ ] Eliminar un viaje
- [ ] Verificar que los cambios se reflejan en los sensores de HA

### Implementation for User Story 3

- [ ] T028 [P] [US3] [VERIFY:BROWSER] Create trip form UI component in custom_components/ev_trip_planner/frontend/panel.js
- [ ] T029 [P] [US3] [VERIFY:BROWSER] Implement trip creation API call in panel.js
- [ ] T030 [P] [US3] [VERIFY:BROWSER] Implement trip edit functionality in panel.js
- [ ] T031 [P] [US3] [VERIFY:BROWSER] Implement trip deletion with confirmation in panel.js
- [ ] T032 [US3] [VERIFY:BROWSER] Display trip list in panel.js
- [ ] T033 [US3] [VERIFY:BROWSER] Add validation for trip destination, date/time, SOC target in panel.js
- [ ] T034 [US3] [VERIFY:API] Call EV Trip Planner services to create/edit/delete trips in panel.js

**Checkpoint**: At this point, User Stories 1, 2, and 3 should all work independently

---

## Phase 6: User Story 4 - Ver perfil de carga diferible (Priority: P2)

**Goal**: Mostrar el perfil de carga diferible cuando EMHASS está configurado

**Independent Test**:
- [ ] Con EMHASS configurado, abrir el panel
- [ ] Verificar que se muestra el gráfico de carga
- [ ] Los datos deben coincidir con el sensor EMHASS

### Tests for User Story 4 (OPTIONAL - only if tests requested) ⚠️

### Implementation for User Story 4

- [ ] T036 [P] [US4] [VERIFY:BROWSER] Check EMHASS configuration status in panel.js
- [ ] T037 [P] [US4] [VERIFY:BROWSER] Fetch EMHASS load profile from HA sensors in panel.js
- [ ] T038 [US4] [VERIFY:BROWSER] Display 24-48 hour load profile chart in panel.js
- [ ] T039 [US4] [VERIFY:BROWSER] Show message when EMHASS not available in panel.js

**Checkpoint**: User Stories 1-4 should all work independently

---

## Phase 7: User Story 5 - Fallback cuando panel_custom no está disponible (Priority: P2)

**Goal**: Comportamiento degradado apropiado cuando panel_custom falla

**Independent Test**:
- [ ] Simular un entorno donde panel_custom no está disponible
- [ ] Verificar que se usa el fallback de YAML o se muestra un error claro
- [ ] Verificar que el error se registra apropiadamente

### Tests for User Story 5 (OPTIONAL - only if tests requested) ⚠️

- [ ] T040 [P] [US5] [VERIFY:TEST] Test fallback behavior in tests/test_panel_fallback.py (use: python-testing-patterns)

### Implementation for User Story 5

- [ ] T041 [P] [US5] [VERIFY:BROWSER] Detect panel_custom availability in panel.py
- [ ] T042 [P] [US5] [VERIFY:BROWSER] Generate YAML fallback for panel configuration in custom_components/ev_trip_planner/dashboard.py
- [ ] T043 [US5] [VERIFY:BROWSER] Log error with clear message when panel registration fails in panel.py
- [ ] T044 [US5] [VERIFY:API] Notify user about fallback in config flow result in config_flow.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 8: Panel Cleanup & Vehicle Deletion

**Purpose**: Eliminar panel automáticamente cuando se elimina un vehículo

- [ ] T045 [P] [US1] [VERIFY:BROWSER] Implement panel removal in config_flow.py when config entry is removed
- [ ] T046 [P] [US1] [VERIFY:BROWSER] Call frontend.async_remove_panel for vehicle panel in panel.py
- [ ] T047 [US1] [VERIFY:BROWSER] Test panel cleanup on vehicle deletion in tests/test_panel_cleanup.py
- [ ] T048 [US1] [VERIFY:BROWSER] Update panel list when trips are modified (FR-009b) in panel.py

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T049 [P] [P] Documentation updates in docs/ for panel usage
- [ ] T050 [P] [P] Code cleanup and refactoring for panel.js
- [ ] T051 [P] [P] Performance optimization for panel updates
- [ ] T052 [P] [P] Additional unit tests (if requested) in tests/unit/
- [ ] T053 [P] [P] Security hardening for panel access
- [ ] T054 [P] [P] Run quickstart.md validation for panel testing
- [ ] T055 [P] [P] Add CSS polish for better UX in panel.css
- [ ] T056 [P] [P] Add error boundary handling in panel.js

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
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable
- **User Story 4 (P2)**: Depends on US1-3 complete - Requires panel infrastructure
- **User Story 5 (P2)**: Depends on Foundational - Independent error handling

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
- [VERIFY:TEST] = unit/integration tests (pytest)
- [VERIFY:API] = REST API verification (curl to HA)
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Summary Report

**Total Task Count**: 56 tasks

**Task Count by User Story**:
- US1 (Panel Creation): T010-T017, T045-T048 = 11 tasks
- US2 (Vehicle State Display): T018-T025 = 8 tasks
- US3 (Trip CRUD): T026-T034 = 9 tasks
- US4 (EMHASS Profile): T035-T039 = 5 tasks
- US5 (Fallback): T040-T044 = 5 tasks
- Setup & Foundational: T001-T009 = 9 tasks
- Polish & Cleanup: T049-T056 = 8 tasks

**Parallel Opportunities Identified**:
- All [P] marked tasks can run in parallel
- User Stories 1-5 can proceed in parallel after Foundational phase
- Tests for each story can run in parallel

**Independent Test Criteria for Each Story**:
- US1: Panel appears in sidebar after vehicle config
- US2: SOC, autonomy, charging status displayed correctly
- US3: Create/edit/delete trips working from panel
- US4: EMHASS chart shows when configured
- US5: Clear error handling when panel_custom unavailable

**Suggested MVP Scope**: User Story 1 (Panel Creation) + User Story 2 (Vehicle State Display)
- These deliver immediate value: automatic panel creation + basic vehicle information
- Can be deployed independently as MVP
