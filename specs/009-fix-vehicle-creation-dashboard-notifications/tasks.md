# Implementation Tasks - Fix Vehicle Creation, Dashboard, Notifications, CRUD Dashboard, High-Quality Tests

**Feature**: 009-fix-vehicle-creation-dashboard-notifications  
**Status**: Ready for Implementation  
**Created**: 2026-03-20

---

## Dependency Graph

```
Phase 1: Setup
    │
    ▼
Phase 2: Foundational (T001, T002, T003)
    │
    ├──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼
Phase 3: FR-001   Phase 4: FR-002   Phase 5: FR-003   Phase 6: FR-004
(TripManager)    (Dashboard)      (Notifications)    (CRUD Dashboard)
    │              │              │              │
    └──────────────┴──────────────┴──────────────┘
                        │
                        ▼
                Phase 7: FR-005 (Tests)
                        │
                        ▼
                Phase 8: Polish & Logging
```

---

## Phase 1: Setup

**Goal**: Initialize project structure and dependencies

- [ ] T001 [P] Install pytest-homeassistant-custom-component in pyproject.toml
- [ ] T002 [P] Create test fixtures directory structure in tests/

---

## Phase 2: Foundational Tasks

**Goal**: Create blocking prerequisites for all user stories

### T003: Fix trip_manager lookup in sensor.py
**Priority**: Critical  
**Story**: FR-001  
**File**: `custom_components/ev_trip_planner/sensor.py`

**Description**:
- [ ] T003 [US1] Import DATA_RUNTIME constant from __init__.py
- [ ] T003 [US1] Fix namespace lookup in async_setup_entry to use hass.data[DATA_RUNTIME][namespace]
- [ ] T003 [US1] Add logging for trip_manager lookup success/failure
- [ ] T003 [US1] Verify sensors are created with correct trip_manager reference

**Test Criteria**:
- [ ] No "No trip_manager found" errors in log
- [ ] Sensors show valid data after configuration

### T004: Fix dashboard import permissions
**Priority**: High  
**Story**: FR-002  
**File**: `custom_components/ev_trip_planner/__init__.py`

**Description**:
- [ ] T004 [US2] Add storage API fallback method to import_dashboard
- [ ] T004 [US2] Add lovelace.import service fallback method
- [ ] T004 [US2] Add detailed logging for each import attempt
- [ ] T004 [US2] Verify dashboard import succeeds via any method

**Test Criteria**:
- [ ] Dashboard imports successfully if storage is available
- [ ] Dashboard imports via service if storage not available
- [ ] Config flow doesn't fail if dashboard import fails

### T005: Fix notification devices selector
**Priority**: Medium  
**Story**: FR-003  
**File**: `custom_components/ev_trip_planner/config_flow.py`

**Description**:
- [ ] T005 [US3] Verify EntitySelectorConfig uses domain="notify"
- [ ] T005 [US3] Add logging of available notify services
- [ ] T005 [US3] Verify Nabu Casa devices appear in selector
- [ ] T005 [US3] Test multi-select functionality

**Test Criteria**:
- [ ] Nabu Casa devices appear in selector
- [ ] All notify services are visible
- [ ] Multi-select works correctly

---

## Phase 3: User Story 1 - Fix TripManager

**Goal**: Fix trip_manager lookup so all sensors work correctly

**Story**: FR-001 - Fix trip_manager lookup in sensor.py

**Test Criteria**:
- [ ] No "No trip_manager found" errors in log
- [ ] Sensors create successfully during setup
- [ ] Sensors show valid data after configuration

**Tasks**:
- [ ] T006 [US1] Create unit tests for TripManager with mocks
- [ ] T006 [US1] Verify async_setup creates trip_manager correctly
- [ ] T006 [US1] Verify async_add_recurring_trip saves trips
- [ ] T006 [US1] Verify async_add_punctual_trip saves trips
- [ ] T006 [US1] Verify async_update_trip updates trips
- [ ] T006 [US1] Verify async_delete_trip removes trips
- [ ] T006 [US1] Verify async_pause_recurring_trip pauses trips
- [ ] T006 [US1] Verify async_complete_punctual_trip marks complete

---

## Phase 4: User Story 2 - Fix Dashboard Import

**Goal**: Fix dashboard import so Lovelace dashboards are created automatically

**Story**: FR-002 - Fix dashboard import permissions

**Test Criteria**:
- [ ] Dashboard imports successfully if storage is available
- [ ] Dashboard imports via service if storage not available
- [ ] Clear logging of which method was used
- [ ] Config flow doesn't fail if dashboard import fails

**Tasks**:
- [ ] T007 [US2] Create unit tests for import_dashboard
- [ ] T007 [US2] Test storage API import method
- [ ] T007 [US2] Test lovelace.import service fallback
- [ ] T007 [US2] Test lovelace.save service fallback
- [ ] T007 [US2] Verify _load_dashboard_template loads YAML correctly
- [ ] T007 [US2] Verify template variables are substituted correctly

---

## Phase 5: User Story 3 - Fix Notification Selector

**Goal**: Fix notification devices selector so Nabu Casa devices appear

**Story**: FR-003 - Fix notification devices selector

**Test Criteria**:
- [ ] Nabu Casa devices appear in selector
- [ ] All notify services are visible
- [ ] Multi-select works correctly

**Tasks**:
- [ ] T008 [US3] Create unit tests for config flow notification step
- [ ] T008 [US3] Test notification service validation
- [ ] T008 [US3] Test notification devices multi-select
- [ ] T008 [US3] Verify EntitySelectorConfig configuration
- [ ] T008 [US3] Test with mock notify entities

---

## Phase 6: User Story 4 - CRUD Dashboard

**Goal**: Create Lovelace dashboard with complete CRUD functionality for managing trips

**Story**: FR-004 - Implement CRUD dashboard for vehicle trips

**Test Criteria**:
- [ ] Dashboard shows list of trips
- [ ] Dashboard allows creating recurring trips
- [ ] Dashboard allows creating punctual trips
- [ ] Dashboard allows editing trips
- [ ] Dashboard allows deleting trips
- [ ] Dashboard allows completing/pausing trips
- [ ] Dashboard is responsive
- [ ] All changes reflect immediately

**Tasks**:
- [ ] T009 [US4] Create dashboard YAML template with CRUD structure
- [ ] T009 [US4] Implement card for listing recurring trips
- [ ] T009 [US4] Implement card for listing punctual trips
- [ ] T009 [US4] Implement card for creating new trips
- [ ] T009 [US4] Implement card for editing trips
- [ ] T009 [US4] Implement card for deleting trips
- [ ] T009 [US4] Implement card for completing trips
- [ ] T009 [US4] Implement card for pausing trips
- [ ] T009 [US4] Add card-mod styling for consistent appearance
- [ ] T009 [US4] Test dashboard responsiveness on mobile
- [ ] T009 [US4] Test real-time updates after trip changes

**Test Files**:
- [ ] T010 [US4] Create test for dashboard YAML structure
- [ ] T010 [US4] Create test for CRUD operations via services
- [ ] T010 [US4] Create test for dashboard import

---

## Phase 7: User Story 5 - High-Quality Tests

**Goal**: Implement high-quality tests with mocks and fixtures for all functionalities

**Story**: FR-005 - Implement high-quality tests

**Test Criteria**:
- [ ] Unit tests for TripManager
- [ ] Unit tests for VehicleController
- [ ] Integration tests for config_flow
- [ ] Service tests for all services
- [ ] Dashboard tests
- [ ] Notification tests
- [ ] Sensor tests
- [ ] Coverage > 90%
- [ ] All tests pass in CI/CD

**Tasks**:
- [ ] T011 [US5] Create conftest.py with base fixtures
- [ ] T011 [US5] Create MockConfigEntry fixture
- [ ] T011 [US5] Create hass fixture for Home Assistant instance
- [ ] T011 [US5] Create entity_registry fixture
- [ ] T011 [US5] Create device_registry fixture

**Unit Tests - TripManager**:
- [ ] T012 [US5] Create test_trip_manager.py
- [ ] T012 [US5] Test async_setup
- [ ] T012 [US5] Test async_add_recurring_trip
- [ ] T012 [US5] Test async_add_punctual_trip
- [ ] T012 [US5] Test async_update_trip
- [ ] T012 [US5] Test async_delete_trip
- [ ] T012 [US5] Test async_pause_recurring_trip
- [ ] T012 [US5] Test async_complete_punctual_trip
- [ ] T012 [US5] Test async_get_kwh_needed_today
- [ ] T012 [US5] Test async_get_hours_needed_today
- [ ] T012 [US5] Test async_get_next_trip

**Unit Tests - VehicleController**:
- [ ] T013 [US5] Create test_vehicle_controller.py
- [ ] T013 [US5] Test async_setup
- [ ] T013 [US5] Test get_charging_power
- [ ] T013 [US5] Test get_battery_capacity

**Integration Tests - ConfigFlow**:
- [ ] T014 [US5] Create test_config_flow.py
- [ ] T014 [US5] Test async_step_user
- [ ] T014 [US5] Test async_step_sensors
- [ ] T014 [US5] Test async_step_emhass
- [ ] T014 [US5] Test async_step_presence
- [ ] T014 [US5] Test async_step_notifications
- [ ] T014 [US5] Test async_step_init (options flow)

**Service Tests**:
- [ ] T015 [US5] Create test_services.py
- [ ] T015 [US5] Test add_recurring_trip service
- [ ] T015 [US5] Test add_punctual_trip service
- [ ] T015 [US5] Test edit_trip service
- [ ] T015 [US5] Test delete_trip service
- [ ] T015 [US5] Test pause_recurring_trip service
- [ ] T015 [US5] Test resume_recurring_trip service
- [ ] T015 [US5] Test complete_punctual_trip service
- [ ] T015 [US5] Test cancel_punctual_trip service

**Dashboard Tests**:
- [ ] T016 [US5] Create test_dashboard.py
- [ ] T016 [US5] Test import_dashboard
- [ ] T016 [US5] Test _load_dashboard_template
- [ ] T016 [US5] Test _save_lovelace_storage
- [ ] T016 [US5] Test _save_lovelace_import_service

**Notification Tests**:
- [ ] T017 [US5] Create test_notifications.py
- [ ] T017 [US5] Test notification service validation
- [ ] T017 [US5] Test notification devices selection

**Sensor Tests**:
- [ ] T018 [US5] Create test_sensor.py
- [ ] T018 [US5] Test TripPlannerSensor async_update
- [ ] T018 [US5] Test KwhTodaySensor
- [ ] T018 [US5] Test HoursTodaySensor
- [ ] T018 [US5] Test NextTripSensor

---

## Phase 8: Polish & Logging

**Goal**: Add comprehensive logging for troubleshooting and debugging

**Tasks**:
- [ ] T019 [US8] Add DEBUG logging to sensor.py for trip_manager lookup success/failure
- [ ] T019 [US8] Add INFO/ERROR logging to __init__.py for dashboard import attempts
- [ ] T019 [US8] Add DEBUG logging to config_flow.py for each config flow step
- [ ] T019 [US8] Add DEBUG/ERROR logging to trip_manager.py for trip operations
- [ ] T019 [US8] Add ERROR logging with exception context for error handling
- [ ] T019 [US8] Add DEBUG logging for dashboard import method selection

---

## Parallel Execution Opportunities

### Phase 1: Setup
- T001 and T002 can be executed in parallel

### Phase 2: Foundational
- T003, T004, T005 can be executed in parallel (different files)

### Phase 3-6: User Stories
- Each user story phase is independent and can be executed in parallel
- FR-001 (TripManager) → FR-002 (Dashboard) → FR-003 (Notifications) → FR-004 (CRUD)

### Phase 7: Tests
- All test files can be created in parallel
- Test execution should be sequential (depends on implementation)

### Phase 8: Logging
- T019 tasks can be executed in parallel (different files)

---

## Independent Test Criteria

### User Story 1 (FR-001)
- [ ] No "No trip_manager found" errors in log
- [ ] Sensors create successfully during setup
- [ ] Sensors show valid data after configuration

### User Story 2 (FR-002)
- [ ] Dashboard imports successfully if storage is available
- [ ] Dashboard imports via service if storage not available
- [ ] Config flow doesn't fail if dashboard import fails

### User Story 3 (FR-003)
- [ ] Nabu Casa devices appear in selector
- [ ] All notify services are visible
- [ ] Multi-select works correctly

### User Story 4 (FR-004)
- [ ] Dashboard shows list of trips
- [ ] Dashboard allows creating trips
- [ ] Dashboard allows editing trips
- [ ] Dashboard allows deleting trips
- [ ] Dashboard allows completing/pausing trips
- [ ] Dashboard is responsive

### User Story 5 (FR-005)
- [ ] All tests pass in CI/CD
- [ ] Coverage > 90%
- [ ] Tests are independent and reproducible

---

## Suggested MVP Scope

**MVP**: Just User Story 1 (FR-001 - Fix TripManager)

**Rationale**:
- FR-001 is the most critical (blocks all functionality)
- Fixing trip_manager lookup resolves the main error in the log
- All other features depend on working TripManager

**MVP Tasks**:
- T003 [US1] Fix trip_manager lookup in sensor.py
- T012 [US5] Create unit tests for TripManager

**MVP Test Criteria**:
- [ ] No "No trip_manager found" errors in log
- [ ] Sensors create successfully during setup
- [ ] Basic sensors show valid data

---

## Implementation Strategy

1. **MVP First**: Implement FR-001 (TripManager fix) only
2. **Verify MVP**: Run tests and verify no errors in log
3. **Incremental Delivery**: Add FR-002 (Dashboard), then FR-003 (Notifications), etc.
4. **Testing**: Add tests incrementally as features are implemented
5. **Polish**: Add logging and final polish at the end

---

## Task Summary

- **Total Tasks**: 50+ tasks
- **Phase 1 (Setup)**: 2 tasks
- **Phase 2 (Foundational)**: 3 tasks
- **Phase 3 (FR-001)**: 10 tasks
- **Phase 4 (FR-002)**: 6 tasks
- **Phase 5 (FR-003)**: 5 tasks
- **Phase 6 (FR-004)**: 11 tasks
- **Phase 7 (FR-005)**: 18 tasks
- **Phase 8 (Polish)**: 6 tasks

---

## Notes

- All tasks follow the checklist format with checkbox, ID, Story label, and file path
- Tasks are organized by user story for independent implementation
- Parallel execution opportunities identified for efficiency
- MVP scope defined for quick initial delivery
- All test criteria are measurable and verifiable
