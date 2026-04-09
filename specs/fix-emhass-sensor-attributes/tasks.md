# Tasks: fix-emhass-sensor-attributes

**Intent**: BUG_FIX (fixes two bugs in EMHASS sensor)
**Workflow**: Bug TDD (Phase 0 + TDD Red-Green-Yellow phases)
**Total Tasks**: 39

## Phase 0: Bug Reproduction (Document Current State)

- [ ] 0.1 [VERIFY] Document bug #1: device duplication (PASS confirms bug exists)
  - **Do**: Run existing test and confirm it PASSES with buggy behavior (entry_id in identifiers)
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test PASSES showing `{(DOMAIN, "test_entry_id")}` in identifiers (confirms bug is present)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_device_info -v`
  - **Commit**: `test(sensor): document - device_info currently uses entry_id (bug confirmed)`
  - _Requirements: FR-1, AC-1.1_
  - **Note**: This task DOCUMENTS the current buggy state. Task 1.4 will change the expectation to vehicle_id (RED phase).

- [ ] 0.2 [VERIFY] Document bug #2: empty sensor attributes (verify broken data flow)
  - **Do**: Run existing test and confirm attributes are null due to broken data flow
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test shows `power_profile_watts` is None/null (confirms data flow is broken)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor -v`
  - **Commit**: `test(sensor): document - sensor attributes null due to broken caching (bug confirmed)`
  - _Requirements: FR-2, AC-2.1_
  - **Note**: This task DOCUMENTS the current broken state. Tasks 1.24-1.28 will fix the data flow.

## Phase 1: TDD Red-Green-Yellow Cycles

### Cycle 1.1: Coordinator vehicle_id Property

- [ ] 1.1 [RED] Failing test: coordinator exposes vehicle_id property
  - **Do**: Write test asserting `coordinator.vehicle_id` returns vehicle_id from entry.data
  - **Files**: `tests/test_coordinator.py`
  - **Done when**: Test exists AND fails with `AttributeError: 'TripPlannerCoordinator' object has no attribute 'vehicle_id'`
  - **Verify**: `pytest tests/test_coordinator.py -k "test_vehicle_id_property" -v 2>&1 | grep -q "AttributeError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(coordinator): red - failing test for vehicle_id property`
  - _Requirements: FR-9, AC-1.1_

- [ ] 1.2 [GREEN] Add vehicle_id property to TripPlannerCoordinator
  - **Do**: Implement `vehicle_id` property in coordinator.py that reads from entry.data[CONF_VEHICLE_NAME]
  - **Files**: `custom_components/ev_trip_planner/coordinator.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_coordinator.py -k "test_vehicle_id_property" -v`
  - **Commit**: `fix(coordinator): green - add vehicle_id property`
  - _Requirements: FR-9, AC-1.1_
  - **Note**: Fallback already implemented in sensor.py via `getattr(coordinator, 'vehicle_id', entry_id)`

### Cycle 1.2: Fix sensor device_info to use vehicle_id

- [ ] 1.4 [RED] Failing test: device_info uses vehicle_id not entry_id
  - **Do**: Write test asserting `device_info["identifiers"]` contains vehicle_id from coordinator
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test exists AND fails with assertion error (identifiers contains entry_id)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_device_info -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for device_info using vehicle_id`
  - _Requirements: FR-1, AC-1.1_

- [ ] 1.5 [GREEN] Fix device_info to use vehicle_id from coordinator
  - **Do**: Change `device_info` property to use `vehicle_id` from coordinator in identifiers tuple
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_device_info -v`
  - **Commit**: `fix(sensor): green - use vehicle_id in device_info identifiers`
  - _Requirements: FR-1, AC-1.1_

### Cycle 1.3: Fix sensor _attr_name to show vehicle_id

- [ ] 1.7 [RED] Failing test: sensor name shows vehicle_id not UUID
  - **Do**: Write test asserting `_attr_name` contains vehicle_id, not entry_id UUID
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test exists AND fails (name contains entry_id UUID)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_name_uses_vehicle_id -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for _attr_name using vehicle_id`
  - _Requirements: FR-1, AC-1.3_

- [ ] 1.8 [GREEN] Fix _attr_name to use vehicle_id from coordinator
  - **Do**: Change `_attr_name` initialization to use vehicle_id from coordinator instead of entry_id
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_name_uses_vehicle_id -v`
  - **Commit**: `fix(sensor): green - use vehicle_id in _attr_name`
  - _Requirements: FR-1, AC-1.3_

### Cycle 1.4: TripManager publish_deferrable_loads rename (ATOMIC)

- [ ] 1.9 [RED] Failing test: publish_deferrable_loads is public
  - **Do**: Write test asserting `manager.publish_deferrable_loads()` is callable (not private)
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test exists AND fails with `AttributeError` (method is private)
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "test_publish_deferrable_loads_public" -v 2>&1 | grep -q "AttributeError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(trip_manager): red - failing test for public publish_deferrable_loads`
  - _Requirements: FR-10, AC-2.4_

- [ ] 1.10 [GREEN] Rename method AND update ALL 4 internal callers AND fix adapter call (ATOMIC)
  - **Do**: ALL changes in ONE commit to avoid AttributeError crashes:
    1. Rename `_publish_deferrable_loads()` → `publish_deferrable_loads()` (remove underscore)
    2. Update caller at line ~375: `_save_trips()`
    3. Update caller at line ~859: `_async_sync_trip_to_emhass()`
    4. Update caller at line ~887: `_async_remove_trip_from_emhass()`
    5. Update caller at line ~903: `_async_publish_new_trip_to_emhass()`
    6. Change adapter call from `async_publish_all_deferrable_loads()` to `publish_deferrable_loads()`
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: All 6 changes complete AND previously failing test passes AND no AttributeError
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "test_publish_deferrable_loads_public" -v`
  - **Commit**: `refactor(trip_manager): green - rename publish_deferrable_loads to public and update all callers atomically`
  - _Requirements: FR-10, AC-2.4_
  - **Critical**: This is an ATOMIC change - all 6 updates must be in one commit or code crashes

### Cycle 1.5: Update test mocks for renamed method

- [ ] 1.11 [YELLOW] Update mock factory and 2 tests in test_trip_manager_core.py
  - **Do**: Find-and-replace all `_publish_deferrable_loads` → `publish_deferrable_loads` in:
    - `tests/__init__.py` mock factory (~line 127)
    - `tests/test_trip_manager_core.py` line ~774
    - `tests/test_trip_manager_core.py` line ~885
  - **Files**: `tests/__init__.py`, `tests/test_trip_manager_core.py`
  - **Done when**: All 3 locations updated AND all tests pass
  - **Verify**: `pytest tests/test_trip_manager_core.py -v`
  - **Commit**: `refactor(tests): update mock and tests for renamed publish_deferrable_loads method`
  - _Requirements: FR-10, AC-2.4_
  - **Note**: This is mechanical find-and-replace, not TDD (all 3 in one task)

### Cycle 1.6: Fix PresenceMonitor SOC change routing

- [ ] 1.12 [RED] Failing test: SOC change calls publish_deferrable_loads
  - **Do**: Write test asserting `_async_handle_soc_change()` calls `trip_manager.publish_deferrable_loads()`
  - **Files**: `tests/test_presence_monitor_soc.py`
  - **Done when**: Test exists AND fails (method calls async_generate_* instead)
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -k "test_soc_change_calls_publish" -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(presence_monitor): red - failing test for SOC change routing`
  - _Requirements: FR-4, FR-10, AC-3.1_

- [ ] 1.13 [GREEN] Fix PresenceMonitor to call publish_deferrable_loads
  - **Do**: Replace async_generate_* calls with `await self._trip_manager.publish_deferrable_loads()`
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -k "test_soc_change_calls_publish" -v`
  - **Commit**: `fix(presence_monitor): green - route SOC changes to publish_deferrable_loads`
  - _Requirements: FR-4, FR-10, AC-3.1_

- [ ] 1.14 [CRITICAL] Update 6 existing tests in test_presence_monitor_soc.py
  - **Do**: Update ALL existing assertions from `async_generate_*` to `publish_deferrable_loads`:
    - Line ~115-116: `test_soc_change_triggers_recalculation_when_home_and_plugged` (calls assert_called_once)
    - Line ~168-169: `test_soc_change_does_not_trigger_when_away` (calls assert_not_called)
    - Line ~215-216: `test_soc_change_does_not_trigger_when_unplugged` (calls assert_not_called)
    - Line ~364-365: `test_soc_debouncing_5_percent_threshold_blocks_recalculation` (calls assert_not_called)
    - Line ~417-418: `test_soc_debouncing_5_percent_threshold_allows_recalculation` (calls assert_called_once)
    - Line ~469: `test_soc_debouncing_ignores_unavailable_state` (calls assert_not_called)
  - **Files**: `tests/test_presence_monitor_soc.py`
  - **Done when**: All 6 tests updated AND `pytest tests/test_presence_monitor_soc.py -v` passes
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -v`
  - **Commit**: `fix(tests): update existing SOC tests to expect publish_deferrable_loads call`
  - _Requirements: FR-4, FR-10, AC-3.1_
  - **Critical**: If this task is skipped, 6 existing tests will FAIL after task 1.13

- [ ] 1.15 [YELLOW] Refactor: add logging for data flow debug
  - **Do**: Add debug log to track when publish_deferrable_loads is called from SOC change
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Logging added AND tests pass
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -v`
  - **Commit**: `refactor(presence_monitor): yellow - add debug logging for data flow`
  - _Requirements: FR-4, AC-3.5_

### Cycle 1.7: EMHASSAdapter publish_deferrable_loads caching

- [ ] 1.16 [RED] Failing test: publish_deferrable_loads sets cache
  - **Do**: Write test asserting `_cached_power_profile` is set after calling `publish_deferrable_loads()`
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test exists AND fails (cache is None after call)
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_sets_cache" -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(emhass_adapter): red - failing test for cache setting`
  - _Requirements: FR-3, AC-2.4_

- [ ] 1.17 [GREEN] Verify publish_deferrable_loads sets cache (already implemented)
  - **Do**: Verify existing implementation already sets cache correctly (lines 531-533)
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Test confirms cache is set
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_sets_cache" -v`
  - **Commit**: `test(emhass_adapter): green - verify cache setting behavior`
  - _Requirements: FR-3, AC-2.4_
  - **Note**: No YELLOW refactor needed - cache validation is YAGNI for production code

### Cycle 1.8: Coordinator data propagation from EMHASSAdapter

- [ ] 1.18 [RED] Failing test: coordinator data includes EMHASS cache
  - **Do**: Write test asserting `coordinator.data` has EMHASS fields after `publish_deferrable_loads()`
  - **Files**: `tests/test_coordinator.py`
  - **Done when**: Test exists AND fails (data fields are None)
  - **Verify**: `pytest tests/test_coordinator.py -k "test_coordinator_data_emhass_cache" -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(coordinator): red - failing test for EMHASS data propagation`
  - _Requirements: FR-2, AC-2.4_

- [ ] 1.19 [GREEN] Verify coordinator _async_update_data retrieves EMHASS cache
  - **Do**: Verify existing `_async_update_data()` calls `get_cached_optimization_results()` correctly
  - **Files**: `custom_components/ev_trip_planner/coordinator.py`
  - **Done when**: Test confirms data propagation works
  - **Verify**: `pytest tests/test_coordinator.py -k "test_coordinator_data_emhass_cache" -v`
  - **Commit**: `test(coordinator): green - verify EMHASS data propagation`
  - _Requirements: FR-2, AC-2.4_
  - **Note**: No YELLOW refactor needed - data validation in coordinator is YAGNI

## Phase 2: Additional Testing

- [ ] 2.1 Update existing test: _save_trips calls publish_deferrable_loads
  - **Do**: Update `test_async_save_trips_with_emhass_adapter_triggers_publish` to assert `publish_deferrable_loads` not `async_publish_all_deferrable_loads`
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test updated AND passes (line ~1590-1640)
  - **Verify**: `pytest tests/test_trip_manager_core.py::test_async_save_trips_with_emhass_adapter_triggers_publish -v`
  - **Commit**: `test(trip_manager): update save_trips test for publish_deferrable_loads`
  - _Requirements: FR-4, AC-4.1_
  - **Note**: Test already exists, just update assertion to use new method name

- [ ] 2.2 Update existing test: verify _async_sync_trip calls publish_deferrable_loads
  - **Do**: Update test for sync trip to verify `publish_deferrable_loads` is called
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test updated AND passes
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "sync_trip" -v`
  - **Commit**: `test(trip_manager): update sync trip test for publish_deferrable_loads`
  - _Requirements: FR-4, AC-4.2_

- [ ] 2.3 Update existing test: verify _async_remove_trip calls publish_deferrable_loads
  - **Do**: Update test for remove trip to verify `publish_deferrable_loads` is called
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test updated AND passes
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "remove_trip" -v`
  - **Commit**: `test(trip_manager): update remove trip test for publish_deferrable_loads`
  - _Requirements: FR-4, AC-4.3_

- [ ] 2.4 Test: EMHASSAdapter.publish_deferrable_loads calls coordinator refresh
  - **Do**: Write test verifying `coordinator.async_request_refresh()` is called after caching
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test confirms coordinator is notified
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_calls_refresh" -v`
  - **Commit**: `test(emhass_adapter): verify coordinator refresh triggered`
  - _Requirements: FR-3, AC-2.4_

- [ ] 2.5 Test: EmhassDeferrableLoadSensor reads from coordinator.data
  - **Do**: Write test verifying sensor attributes read from coordinator.data EMHASS fields
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test confirms data flow coordinator -> sensor
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_reads_coordinator_data -v`
  - **Commit**: `test(sensor): verify sensor reads coordinator.data`
  - _Requirements: FR-2, AC-2.4_

## Phase 3: Quality Gates

- [ ] 3.1 [VERIFY] Quality checkpoint: lint and format
  - **Do**: Run ruff linting and format check on all modified files
  - **Files**: `custom_components/ev_trip_planner/coordinator.py`, `sensor.py`, `presence_monitor.py`, `trip_manager.py`, `emhass_adapter.py`, `tests/`
  - **Done when**: All linting passes
  - **Verify**: `ruff check . && mypy custom_components/ tests/ --no-namespace-packages`
  - **Commit**: `chore: pass linting and type checking`
  - _Requirements: NFR-2_

- [ ] 3.2 [VERIFY] Quality checkpoint: unit tests pass with 100% coverage
  - **Do**: Run full test suite with coverage report
  - **Files**: All modified modules
  - **Done when**: All tests pass and coverage is 100% for affected modules
  - **Verify**: `pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Commit**: `chore: achieve 100% coverage for modified modules`
  - _Requirements: NFR-2, AC-T1.4_

- [ ] 3.3 [VERIFY] Quality checkpoint: existing tests still pass
  - **Do**: Run all existing sensor tests to ensure no regression
  - **Files**: `tests/test_deferrable_load_sensors.py`, `tests/test_trip_manager_core.py`
  - **Done when**: All existing tests pass
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py tests/test_trip_manager_core.py -v`
  - **Commit**: `chore: verify no regression in existing tests`
  - _Requirements: AC-T1.1_

## Phase 4: E2E Testing

- [ ] 4.1 [VE0] E2E: ui-map-init for EMHASS sensor updates
  - **Do**: Build selector map for EMHASS sensor state inspection and developer tools page
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: Selector map file exists with HA developer tools and EMHASS sensor selectors
  - **Verify**: `grep -q "EMHASS_STATE_SELECTOR" tests/e2e/emhass-sensor-updates.spec.ts && echo VE0_PASS`
  - **Commit**: `test(e2e): ui-map-init for EMHASS sensor updates`
  - _Requirements: AC-T2.1_

- [ ] 4.2 [VE1-STARTUP] E2E: startup handled by make e2e
  - **Do**: The `make e2e` script handles HA startup automatically. No manual startup needed.
  - **Files**: `Makefile`, `scripts/run-e2e.sh`
  - **Done when**: `make e2e` successfully starts HA and runs tests
  - **Verify**: `make e2e` shows HA startup logs and begins test execution
  - **Commit**: (No commit - documentation only)
  - _Requirements: AC-T2.5_
  - **Note**: E2E startup/cleanup are handled by the existing make e2e workflow

- [ ] 4.3 [VE2-CHECK] E2E: create trip and verify EMHASS sensor updates
  - **Do**: Navigate to panel, create trip via UI, check developer tools > states for sensor attributes
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: `power_profile_watts` has non-zero values after trip creation
  - **Verify**: `npx playwright test emhass-sensor-updates.spec.ts --project=chromium`
  - **Commit**: `test(e2e): verify EMHASS sensor updates after trip creation`
  - _Requirements: AC-T2.2, AC-2.1_

- [ ] 4.4 [VE2-CHECK] E2E: simulate SOC change and verify sensor update
  - **Do**: Change SOC sensor state via HA API, verify `emhass_status` changes
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: Sensor reflects new SOC-based state (idle -> ready or vice versa)
  - **Verify**: `npx playwright test emhass-sensor-updates.spec.ts --project=chromium`
  - **Commit**: `test(e2e): verify EMHASS sensor updates after SOC change`
  - _Requirements: AC-T2.3, AC-3.5_

- [ ] 4.5 [VE2-CHECK] E2E: verify single device in HA UI
  - **Do**: Navigate to Developer Tools > States, verify only one device exists for vehicle_id
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: Device list shows single "EV Trip Planner {vehicle_id}" device with 8 entities
  - **Verify**: `npx playwright test emhass-sensor-updates.spec.ts --project=chromium`
  - **Commit**: `test(e2e): verify single device per vehicle in HA UI`
  - _Requirements: AC-1.2, AC-1.3_

- [ ] 4.6 [VE3-CLEANUP] E2E: cleanup handled by make e2e
  - **Do**: The `make e2e` script handles HA shutdown and cleanup automatically. No manual cleanup needed.
  - **Files**: `Makefile`, `scripts/run-e2e.sh`
  - **Done when**: `make e2e` completes with exit code 0 after cleanup
  - **Verify**: `make e2e` shows cleanup logs and exits cleanly
  - **Commit**: (No commit - documentation only)
  - _Requirements: AC-T2.5_
  - **Note**: E2E cleanup is handled by the existing make e2e workflow

## Phase 5: PR and Documentation

- [ ] 5.1 Create PR with descriptive title and body
  - **Do**: Create PR summarizing both bug fixes, including before/after screenshots if possible
  - **Files**: `.github/` (PR creation via gh CLI or web)
  - **Done when**: PR is created and ready for review
  - **Verify**: `gh pr view --json title,body | jq -r '.title' | grep -q "fix.*emhass.*sensor"`
  - **Commit**: (N/A - PR commit created by gh)
  - _Requirements: Documentation_

- [ ] 5.2 Update CHANGELOG with bug fixes
  - **Do**: Document both bug fixes in changelog with issue references
  - **Files**: `CHANGELOG.md` (or create if not exists)
  - **Done when**: Changelog entries added for device duplication and empty attributes fixes
  - **Verify**: `grep -q "fix(emhass)" CHANGELOG.md && echo CHANGELOG_PASS`
  - **Commit**: `docs: update CHANGELOG for EMHASS sensor bug fixes`
  - _Requirements: Documentation_

- [ ] 5.3 [VF] [VERIFY] Goal verification: original bugs now fixed
  - **Do**:
    1. Read `## Reality Check (BEFORE)` from .progress.md
    2. Re-run reproduction commands to verify both bugs are fixed
    3. Confirm device_info uses vehicle_id and sensor attributes are populated
  - **Files**: `specs/fix-emhass-sensor-attributes/.progress.md`
  - **Done when**: Both reproduction commands now pass
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor -v | grep -q "PASSED"`
  - **Commit**: `chore: verify fix resolves original EMHASS sensor bugs`
  - _Requirements: FR-1, FR-2, Success Criteria_

---

## Task Summary

**Total Tasks**: 39 (reduced from 53 by removing YAGNI tasks, merging atomic changes, and eliminating duplicates)
**Phase 0**: 2 tasks (bug reproduction - document current state)
**Phase 1**: 17 tasks (TDD cycles - reduced by removing 5 YAGNI refactor tasks)
**Phase 2**: 5 tasks (update existing tests - 2.4/2.5 removed as covered by 1.14)
**Phase 3**: 3 tasks (quality gates)
**Phase 4**: 6 tasks (E2E testing)
**Phase 5**: 6 tasks (PR, documentation, edge cases)
**Quality checkpoints**: 3 (after each phase group)

---

## Phase 5 Extended: Edge Cases and Integration

- [ ] 5.4 Test: vehicle_id changes gracefully handled
  - **Do**: Write test verifying sensor handles vehicle_id rename in config without crash
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test confirms fallback behavior works when vehicle_id changes
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_vehicle_id_change -v`
  - **Commit**: `test(sensor): verify vehicle_id change handling`
  - _Requirements: Edge case - vehicle_id changes_

- [ ] 5.5 Test: EMHASSAdapter handles no trips gracefully
  - **Do**: Write test verifying `publish_deferrable_loads()` handles empty trip list without error
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test confirms all-zero profile is cached for empty trips
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_empty_trips" -v`
  - **Commit**: `test(emhass_adapter): verify empty trips handling`
  - _Requirements: Edge case - no trips configured_

- [ ] 5.6 Test: EMHASSAdapter handles None coordinator gracefully
  - **Do**: Write test verifying `publish_deferrable_loads()` logs warning when coordinator is None
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test confirms early return with warning when no coordinator
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_no_coordinator" -v`
  - **Commit**: `test(emhass_adapter): verify None coordinator handling`
  - _Requirements: Edge case - coordinator not available_

---

## Notes

1. **Bug TDD Workflow**: Phase 0 DOCUMENTS current buggy state (tests PASS with bugs), then TDD cycles fix them
2. **Atomic Rename**: Task 1.10 is ATOMIC - all 6 changes (method rename + 4 callers + adapter call) in ONE commit to avoid AttributeError crashes
3. **Critical Task 1.14**: Updates 6 existing tests in test_presence_monitor_soc.py - if skipped, existing tests FAIL after task 1.13
4. **Existing Tests Updated**: Phase 2 tasks UPDATE existing tests, not create new ones (tasks 2.4/2.5 removed as covered by 1.14)
5. **YAGNI Tasks Removed**: 5 refactor tasks removed (1.3, 1.6, 1.9, 1.26, 1.29) - speculative validation/helpers not needed
6. **E2E Testing**: Tasks 4.2 and 4.6 delegate to `make e2e` workflow - no manual startup/cleanup needed
7. **Coverage**: Affected modules must maintain 100% line coverage (NFR-2)
8. **Total**: 39 tasks (reduced from 53 by removing YAGNI, merging atomic changes, and eliminating duplicates)
