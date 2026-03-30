# Tasks: Trip Card Enhancement

## Phase 1: TDD Red-Green-Yellow Cycles

Focus: Display p_deferrable_index and charging window on trip cards via TripSensor extra_state_attributes.

### Trip 1: p_deferrable_index Display

- [x] 1.1 [RED] Failing test: TripSensor shows p_deferrable_index in extra_state_attributes
  - **Do**:
    1. Open `tests/test_sensor.py`
    2. Add test `test_trip_sensor_p_deferrable_index_attribute` that:
       - Creates a TripSensor with trip_data containing id="trip_001", tipo="recurrente"
       - Mocks trip_manager.emhass_adapter.get_assigned_index("trip_001") to return 5
       - Asserts `sensor.extra_state_attributes["p_deferrable_index"] == 5`
  - **Files**: tests/test_sensor.py
  - **Done when**: Test exists AND fails with AssertionError (p_deferrable_index not in attributes)
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_p_deferrable_index" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(trip-card): red - failing test for p_deferrable_index attribute`
  - _Requirements: AC-1_
  - _Design: Interface Contracts_

- [x] 1.2 [GREEN] Pass test: Add p_deferrable_index to TripSensor extra_state_attributes
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. In `TripSensor.__init__()`, get emhass_adapter from trip_manager
    3. Call `emhass_adapter.get_assigned_index(trip_id)` to get the index
    4. Add `p_deferrable_index` to `_attr_extra_state_attributes` dict
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: TripSensor extra_state_attributes includes p_deferrable_index when EMHASS configured
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_p_deferrable_index" 2>&1 | tail -10`
  - **Commit**: `feat(trip-card): green - add p_deferrable_index to TripSensor`
  - _Requirements: AC-1_
  - _Design: Interface Contracts_

### Trip 2: charging_window Display

- [x] 1.3 [RED] Failing test: TripSensor shows charging_window in extra_state_attributes
  - **Do**:
    1. Open `tests/test_sensor.py`
    2. Add test `test_trip_sensor_charging_window_attribute` that:
       - Creates a TripSensor with trip_data containing ventana_carga with inicio_ventana="2026-03-30T18:00:00", fin_ventana="2026-03-30T22:00:00"
       - Asserts `sensor.extra_state_attributes["charging_window"]["start"] == "18:00"`
       - Asserts `sensor.extra_state_attributes["charging_window"]["end"] == "22:00"`
  - **Files**: tests/test_sensor.py
  - **Done when**: Test exists AND fails with AssertionError
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_charging_window" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(trip-card): red - failing test for charging_window attribute`
  - _Requirements: AC-2_
  - _Design: Interface Contracts_

- [x] 1.4 [GREEN] Pass test: Add charging_window to TripSensor extra_state_attributes
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. In `TripSensor.__init__()`, extract ventana_carga from trip_data
    3. If ventana_carga exists, add charging_window dict with start/end times formatted as HH:MM
    4. Add to `_attr_extra_state_attributes`
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: TripSensor extra_state_attributes includes charging_window with start/end when trip has ventana_carga
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_charging_window" 2>&1 | tail -10`
  - **Commit**: `feat(trip-card): green - add charging_window to TripSensor`
  - _Requirements: AC-2_
  - _Design: Interface Contracts_

### Trip 3: soc_target Display

- [x] 1.5 [YELLOW] Refactor: Extract _get_emhass_info() helper method
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. Find the pattern where p_deferrable_index is added to _attr_extra_state_attributes
    3. Extract into `_get_emhass_info()` method that returns dict with all EMHASS-related attributes
    4. Keep code DRY - this helper will be used by both p_deferrable_index and future soc_target
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Code refactored, tests still pass
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "p_deferrable_index or charging_window" 2>&1 | tail -10`
  - **Commit**: `refactor(trip-card): extract _get_emhass_info helper`
  - _Requirements: AC-1, AC-2_
  - _Design: Architecture_

- [ ] 1.6 [GREEN] Pass test: Add soc_target to TripSensor extra_state_attributes
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. In `TripSensor.__init__()`, extract soc_objetivo from trip_data
    3. Add `soc_target` to `_attr_extra_state_attributes`
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: TripSensor extra_state_attributes includes soc_target when trip has it
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_soc_target" 2>&1 | tail -10`
  - **Commit**: `feat(trip-card): green - add soc_target to TripSensor`
  - _Requirements: AC-3_
  - _Design: Interface Contracts_

### Trip 4: deficit_from_previous Display

- [ ] 1.7 [RED] Failing test: TripSensor shows deficit_from_previous in extra_state_attributes
  - **Do**:
    1. Open `tests/test_sensor.py`
    2. Add test `test_trip_sensor_deficit_attribute` that:
       - Creates a TripSensor with trip_data containing deficit_acumulado=5.0
       - Asserts `sensor.extra_state_attributes["deficit_from_previous"] == 5.0`
  - **Files**: tests/test_sensor.py
  - **Done when**: Test exists AND fails with AssertionError
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_deficit" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(trip-card): red - failing test for deficit_from_previous attribute`
  - _Requirements: AC-3_
  - _Design: Interface Contracts_

- [ ] 1.8 [GREEN] Pass test: Add deficit_from_previous to TripSensor extra_state_attributes
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. In `TripSensor.__init__()`, extract deficit_acumulado from trip_data
    3. Add `deficit_from_previous` to `_attr_extra_state_attributes`
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: TripSensor extra_state_attributes includes deficit_from_previous when trip has deficit_acumulado
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_deficit" 2>&1 | tail -10`
  - **Commit**: `feat(trip-card): green - add deficit_from_previous to TripSensor`
  - _Requirements: AC-3_
  - _Design: Interface Contracts_

### Trip 5: EMHASS Not Configured Case

- [ ] 1.9 [RED] Failing test: TripSensor handles EMHASS not configured gracefully
  - **Do**:
    1. Open `tests/test_sensor.py`
    2. Add test `test_trip_sensor_no_emhass_attributes` that:
       - Creates a TripSensor with trip_manager where emhass_adapter is None
       - Mocks trip_manager.get_emhass_adapter() to return None
       - Asserts `sensor.extra_state_attributes` does NOT contain p_deferrable_index
       - Or asserts p_deferrable_index is None/absent
  - **Files**: tests/test_sensor.py
  - **Done when**: Test exists AND fails with AssertionError
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_no_emhass" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(trip-card): red - failing test for EMHASS not configured case`
  - _Requirements: AC-5_
  - _Design: AC-5_

- [ ] 1.10 [GREEN] Pass test: Handle EMHASS not configured in TripSensor
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. In `TripSensor.__init__()`, check if trip_manager has emhass_adapter
    3. If no emhass_adapter or get_emhass_adapter() returns None, skip p_deferrable_index
    4. Ensure other attributes (charging_window, soc_target, deficit) still work without EMHASS
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: TripSensor works without EMHASS, p_deferrable_index not added when EMHASS unavailable
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "test_trip_sensor_no_emhass" 2>&1 | tail -10`
  - **Commit**: `feat(trip-card): green - handle EMHASS not configured case`
  - _Requirements: AC-5_
  - _Design: AC-5_

- [ ] 1.11 [VERIFY] Quality checkpoint: All TDD tests pass
  - **Do**: Run all trip-card enhancement tests
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "p_deferrable_index or charging_window or soc_target or deficit or no_emhass" 2>&1 | tail -20`
  - **Done when**: All 5 tests pass
  - **Commit**: `chore(trip-card): pass TDD quality checkpoint`

## Phase 2: Update Methods

Update `update_from_trip_data` to include new attributes when trip is edited.

- [ ] 2.1 [RED] Failing test: update_from_trip_data preserves new attributes
  - **Do**:
    1. Open `tests/test_sensor.py`
    2. Add test `test_trip_sensor_update_from_trip_data_new_attributes` that:
       - Creates TripSensor with trip_data containing ventana_carga and soc_objetivo
       - Calls `sensor.update_from_trip_data(updated_trip_data)`
       - Asserts extra_state_attributes includes charging_window, soc_target
  - **Files**: tests/test_sensor.py
  - **Done when**: Test exists AND fails with AssertionError
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "update_from_trip_data_new" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(trip-card): red - failing test for update_from_trip_data new attributes`
  - _Requirements: AC-4_
  - _Design: AC-4_

- [ ] 2.2 [GREEN] Pass test: Update update_from_trip_data to include new attributes
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. Find `update_from_trip_data` method in TripSensor
    3. Add the same logic for charging_window, soc_target, deficit_from_previous as in __init__
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: update_from_trip_data includes all new attributes
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "update_from_trip_data_new" 2>&1 | tail -10`
  - **Commit**: `feat(trip-card): green - update update_from_trip_data with new attributes`
  - _Requirements: AC-4_
  - _Design: AC-4_

- [ ] 2.3 [VERIFY] Quality checkpoint: update tests pass
  - **Do**: Run update tests
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short -k "update_from_trip_data" 2>&1 | tail -15`
  - **Done when**: All update tests pass
  - **Commit**: `chore(trip-card): pass update quality checkpoint`

## Phase 3: Quality Gates

- [ ] 3.1 [VERIFY] Local lint check
  - **Do**: Run ruff and pylint on modified files
  - **Verify**: `ruff check custom_components/ev_trip_planner/sensor.py && pylint custom_components/ev_trip_planner/sensor.py 2>&1 | tail -20`
  - **Done when**: No lint errors
  - **Commit**: `chore(trip-card): fix lint issues` (if needed)

- [ ] 3.2 [VERIFY] Type check
  - **Do**: Run mypy on modified files
  - **Verify**: `mypy custom_components/ev_trip_planner/sensor.py --no-namespace-packages 2>&1 | tail -20`
  - **Done when**: No type errors
  - **Commit**: `chore(trip-card): fix type issues` (if needed)

- [ ] 3.3 [VERIFY] All tests pass
  - **Do**: Run full test suite
  - **Verify**: `python3 -m pytest tests/test_sensor.py -v --tb=short 2>&1 | tail -30`
  - **Done when**: All sensor tests pass
  - **Commit**: `chore(trip-card): pass test suite` (if needed)

- [ ] 3.4 [VERIFY] Full local CI
  - **Do**: Run make check (test, lint, mypy)
  - **Verify**: `make check 2>&1 | tail -40`
  - **Done when**: All checks pass
  - **Commit**: `chore(trip-card): pass local CI`

- [ ] 3.5 [VERIFY] AC checklist
  - **Do**: Verify each AC is satisfied:
    - AC-1: `grep -n "p_deferrable_index" custom_components/ev_trip_planner/sensor.py`
    - AC-2: `grep -n "charging_window" custom_components/ev_trip_planner/sensor.py`
    - AC-3: `grep -n "soc_target\|deficit_from_previous" custom_components/ev_trip_planner/sensor.py`
    - AC-4: `grep -n "update_from_trip_data" custom_components/ev_trip_planner/sensor.py`
    - AC-5: `grep -n "get_emhass_adapter\|emhass_adapter" custom_components/ev_trip_planner/sensor.py`
  - **Verify**: All grep commands return results
  - **Done when**: All acceptance criteria verified in code
  - **Commit**: None

## Phase 4: PR Lifecycle

- [ ] 4.1 Create PR and verify CI
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin feature/soc-milestone-algorithm`
    3. Create PR using gh CLI
  - **Verify**: `gh pr checks --watch` or `gh pr checks`
  - **Done when**: All CI checks green
  - **If CI fails**: Fix issues locally and push

- [ ] 4.2 PR Lifecycle loop
  - **Do**: Monitor CI, address review comments, push fixes
  - **Done when**: PR approved and merged
  - **Verify**: PR shows merged status

## Notes

- **TDD approach**: All implementation driven by failing tests first
- **Size**: Small - UI display logic only
- **Dependencies**: emhass-sensor-enhancement (completed) - provides get_assigned_index method
- **Interface**: TripSensor extra_state_attributes extended with p_deferrable_index, charging_window, soc_target, deficit_from_previous
