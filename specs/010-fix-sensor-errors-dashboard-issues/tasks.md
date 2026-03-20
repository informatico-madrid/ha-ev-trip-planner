---

description: "Task list for fixing sensor errors, dashboard issues in Home Assistant Container"

---

# Tasks: Fix Sensor Errors, Dashboard Issues

**Input**: Design documents from `/specs/010-fix-sensor-errors-dashboard-issues/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: Following TDD - tests must be written FIRST, then implementation

**Organization**: Tasks grouped by bug fix priority (P001 → P003 → P002 → P004)

---

## Skills Required

**MUST use these skills for relevant tasks**:

| Task Types | Skill | Purpose |
|-----------|-------|---------|
| All test tasks | `python-testing-patterns` | pytest, fixtures, mocking, TDD |
| HA sensor code | `homeassistant-best-practices` | HA entity patterns, sensor config |
| Dashboard YAML | `homeassistant-dashboard-designer` | Lovelace dashboard config |
| HA config | `homeassistant-config` | YAML configuration |

**IMPORTANT**: Load skill before implementing tasks. Use: `/skill python-testing-patterns`

---

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Verification)

**Purpose**: Verify current test state before making changes

- [ ] T001 Verify existing tests pass: `cd src && pytest tests/ -v`

---

## Phase 2: P001 - VehicleController.get_charging_power() (CRITICAL)

**Goal**: Fix AttributeError occurring every 30 seconds

**Test**: Test must FAIL before implementation

### Tests for P001

- [ ] T002 [P] [P001] Add test reproducing get_charging_power error in tests/test_trip_manager_core.py
  - Test should call `trip_manager.get_charging_power()` 
  - Expected: FAIL with AttributeError before fix
  - **Skill**: Use `python-testing-patterns` for pytest fixtures

### Implementation for P001

- [ ] T003 [P001] Add public get_charging_power() method in custom_components/ev_trip_planner/trip_manager.py
  - Method should call internal `_get_charging_power()`
  - Add type hints and docstring
  - Returns: kW (kilowatts)

- [ ] T004 [P001] Update sensor.py line 90 to use trip_manager.get_charging_power()
  - Change: `self.trip_manager.vehicle_controller.get_charging_power()`
  - To: `self.trip_manager.get_charging_power()`
  - **Skill**: Use `homeassistant-best-practices` for sensor patterns

### Verification P001

- [ ] T005 Run test to verify fix: `cd src && pytest tests/test_trip_manager_core.py -v -k charging_power`

---

## Phase 3: P003 - NextTripSensor failure (ERROR)

**Goal**: Fix ValueError when sensor creates without trips

**Test**: Test must FAIL before implementation

### Tests for P003

- [ ] T006 [P] [P003] Add test for NextTripSensor with no trips in tests/test_sensor_coverage.py
  - Test should create sensor with empty trip list
  - Expected: FAIL with ValueError before fix
  - **Skill**: Use `python-testing-patterns` for pytest fixtures

### Implementation for P003

- [ ] T007 [P003] Remove device_class from NextTripSensor in custom_components/ev_trip_planner/sensor.py
  - Find NextTripSensor class definition
  - Remove `_attr_device_class` attribute
  - Remove `_attr_state_class` attribute  
  - Remove `_attr_native_unit_of_measurement` attribute
  - **Skill**: Use `homeassistant-best-practices` for sensor entity config

### Verification P003

- [ ] T008 Run test to verify fix: `cd src && pytest tests/test_sensor_coverage.py -v -k next_trip`

---

## Phase 4: P002 - Device class sensors (WARNING)

**Goal**: Fix warnings about incompatible device_class

**Test**: Test must FAIL before implementation

### Tests for P002

- [ ] T009 [P] [P002] Add test validating device_class for each sensor type in tests/test_sensor.py
  - Test: KwhTodaySensor should have device_class ENERGY
  - Test: HoursTodaySensor should NOT have device_class ENERGY
  - Test: NextTripSensor should NOT have device_class ENERGY
  - Test: Count sensors should NOT have device_class ENERGY
  - Expected: FAIL for non-energy sensors before fix
  - **Skill**: Use `python-testing-patterns` for pytest fixtures

### Implementation for P002

- [ ] T010 [P002] Remove device_class from TripPlannerSensor base class in sensor.py lines 58-60
  - Remove: `_attr_state_class`, `_attr_device_class`, `_attr_native_unit_of_measurement`
  - **Skill**: Use `homeassistant-best-practices` for sensor patterns

- [ ] T011 [P002] Add device_class to KwhTodaySensor in sensor.py
  - Add: `_attr_device_class = SensorDeviceClass.ENERGY`
  - Add: `_attr_state_class = SensorStateClass.MEASUREMENT`
  - Add: `_attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR`
  - **Skill**: Use `homeassistant-best-practices` for sensor entity config

- [ ] T012 [P] [P002] Add device_class to HoursTodaySensor in sensor.py
  - Add: `_attr_native_unit_of_measurement = UnitOfTime.HOURS` (or None)
  - Add: `_attr_state_class = SensorStateClass.MEASUREMENT`
  - **Skill**: Use `homeassistant-best-practices` for sensor entity config

### Verification P002

- [ ] T013 Run test to verify fix: `cd src && pytest tests/test_sensor.py -v -k device_class`

---

## Phase 5: P004 - Dashboard Container (ERROR)

**Goal**: Fix dashboard import in Home Assistant Container

**Test**: Test must FAIL before implementation

### Tests for P004

- [ ] T014 [P] [P004] Add test for Container environment in tests/test_dashboard.py
  - Mock: `hass.services.has_service` returns False
  - Mock: `hass.storage` not available
  - Expected: FAIL before fix
  - **Skill**: Use `python-testing-patterns` for mocking HA services

- [ ] T014b [P] [P004] Add test for duplicate dashboard name collision in tests/test_dashboard.py
  - Test: Import dashboard when name already exists
  - Expected: Should append suffix (-2-, -3-)
  - **Skill**: Use `python-testing-patterns` for edge case testing

- [ ] T014c [P] [P004] Add test for all failure modes in tests/test_dashboard.py
  - Test: No partial failures - all error cases handled
  - Expected: Robust behavior for all edge cases
  - **Skill**: Use `python-testing-patterns` for robust error handling tests

### Implementation for P004

- [ ] T015 [P004] Implement Container fallback in custom_components/ev_trip_planner/__init__.py
  - Add check: detect Container environment
  - Generate YAML file to config directory
  - Log clear instructions for manual import
  - Return informative error message
  - **Skill**: Use `homeassistant-ops` for HA API patterns, `homeassistant-dashboard-designer` for YAML

- [ ] T015b [P004] Implement duplicate name handling in __init__.py
  - Check if dashboard path already exists
  - Append suffix (-2-, -3-) to make unique
  - Test all collision scenarios
  - **Skill**: Use `homeassistant-config` for YAML configuration

### Verification P004

- [ ] T016 Run test to verify fix: `cd src && pytest tests/test_dashboard.py -v -k container`
- [ ] T016b Run test for duplicate name: `cd src && pytest tests/test_dashboard.py -v -k duplicate`

---

## Phase 6: Polish

**Purpose**: Final verification and cleanup

- [ ] T017 Run full test suite: `cd src && pytest tests/ -v --cov=custom_components/ev_trip_planner`
- [ ] T018 Verify coverage >= 80% (per Constitution requirement)
  - Run: `cd src && pytest tests/ --cov=custom_components/ev_trip_planner --cov-report=term-missing`
  - If coverage < 80%: Add more tests to cover missing lines
  - **Skill**: Use `python-testing-patterns` for coverage analysis
- [ ] T019 Check logs for any remaining errors
- [ ] T020 Ensure all new code paths are covered by tests
  - Every new method/function must have at least one test
  - Every edge case (None, empty, error) must be tested

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify baseline first
- **P001 (Phase 2)**: Critical - blocks crashes
- **P003 (Phase 3)**: Error - sensor fails to create
- **P002 (Phase 4)**: Warning - logs pollution
- **P004 (Phase 5)**: Error - dashboard doesn't work
- **Polish (Phase 6)**: After all fixes

### Execution Order (by priority)

```
Phase 1 (Setup) → P001 (CRITICAL) → P003 (ERROR) → P002 (WARNING) → P004 (ERROR) → Polish (T017-T020)
```

### Coverage Requirement (CRITICAL)

Per Constitution: **MUST achieve >= 80% test coverage**

- T018: Verify coverage >= 80%
- T020: Ensure all new code paths have tests

If coverage < 80% after all fixes:
- Add more tests for untested paths
- Re-run coverage until passing
- **This is a mandatory gate - cannot proceed without 80%+**

### Within Each Fix

1. Write failing test first (use `python-testing-patterns`)
2. Run test to confirm failure
3. Implement fix (use `homeassistant-best-practices`)
4. Run test to confirm pass
5. Run full test suite

---

## Parallel Opportunities

- **T002, T006, T009, T014**: All test creation tasks can run in parallel
- **T003, T010, T011**: Implementation tasks in different files can run in parallel
- **P002 and P004**: Can be implemented in parallel (different files)

---

## Notes

- **TDD**: All fixes follow Test-Driven Development - tests first!
- **Critical first**: P001 causes crashes every 30 seconds
- **All existing tests must still pass** after changes
- **HA Container**: No Supervisor, special handling needed
- **Commit after each task**: Small, focused commits
- **Skills**: MUST load relevant skills before implementing tasks
