# Tasks: emhass-integration-with-fixes

## Phase 1: Red-Green-Yellow Cycles

Focus: Test-driven integration of cascade delete, sensor sync, dashboard sync, trip state updates, and error notifications.

### AC-1: Cascade Delete Integration

- [ ] 1.1 [RED] Failing test: Vehicle deletion removes all trips from TripManager storage
  - **Do**: Write test in `tests/test_integration_uninstall.py` asserting `async_delete_all_trips()` is called during `async_unload_entry`
  - **Files**: `tests/test_integration_uninstall.py`
  - **Done when**: Test exists AND fails with assertion error (method not called)
  - **Verify**: `python3 -m pytest tests/test_integration_uninstall.py -k "cascade" -v 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(cascade): red - failing test for cascade delete`
  - _Requirements: AC-1_
  - _Design: Integration Points - TripManager -> EMHASSAdapter_

- [ ] 1.2 [GREEN] Pass test: Implement cascade delete in async_unload_entry
  - **Do**: In `__init__.py`, modify `async_unload_entry()` to call `trip_manager.async_delete_all_trips()` before cleanup
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `python3 -m pytest tests/test_integration_uninstall.py -k "cascade" -v`
  - **Commit**: `fix(uninstall): implement cascade delete for trips`
  - _Requirements: AC-1_

- [ ] 1.3 [YELLOW] Refactor: Ensure EMHASS adapter indices are cleaned up
  - **Do**: Review `emhass_adapter.py` for index cleanup on vehicle delete, add `async_cleanup_vehicle_indices()` if missing
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: All EMHASS indices for deleted vehicle are released
  - **Verify**: `python3 -m pytest tests/test_emhass_adapter.py -v`
  - **Commit**: `refactor(emhass): cleanup indices on vehicle delete`

### AC-2: Sensor Creation on Vehicle Add

- [ ] 1.4 [RED] Failing test: Vehicle addition creates EmhassDeferrableLoadSensor
  - **Do**: Write test asserting `EmhassDeferrableLoadSensor` is created when vehicle config completes
  - **Files**: `tests/test_sensor_coverage.py`
  - **Done when**: Test exists AND fails (sensor not created)
  - **Verify**: `python3 -m pytest tests/test_sensor_coverage.py -k "emhass_deferrable" -v 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(sensors): red - failing test for EmhassDeferrableLoadSensor creation`
  - _Requirements: AC-2_

- [ ] 1.5 [GREEN] Pass test: Ensure EmhassDeferrableLoadSensor is created on vehicle setup
  - **Do**: In `sensor.py`, verify `EmhassDeferrableLoadSensor` class exists and is properly registered in HA
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Sensor class exists and test passes
  - **Verify**: `python3 -m pytest tests/test_sensor_coverage.py -k "emhass_deferrable" -v`
  - **Commit**: `feat(sensors): ensure EmhassDeferrableLoadSensor registration`
  - _Requirements: AC-2_

- [ ] 1.6 [YELLOW] Refactor: Verify sensor creation is triggered from async_setup_entry
  - **Do**: Check `__init__.py` `async_setup_entry()` calls sensor creation, ensure TripManager.set_emhass_adapter() is called
  - **Files**: `custom_components/ev_trip_planner/__init__.py`, `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Sensor creation flow verified
  - **Verify**: `grep -n "set_emhass_adapter\|EmhassDeferrableLoadSensor" custom_components/ev_trip_planner/__init__.py`
  - **Commit**: `refactor(sensors): verify sensor creation in setup flow`

### AC-3: Dashboard Data Synchronization

- [ ] 1.7 [RED] Failing test: Dashboard loads and syncs data from TripManager
  - **Do**: Write test verifying `trip_manager.get_all_trips()` returns correct data when dashboard loads
  - **Files**: `tests/test_dashboard.py`
  - **Done when**: Test exists AND fails (data not syncing)
  - **Verify**: `python3 -m pytest tests/test_dashboard.py -k "sync" -v 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(dashboard): red - failing test for dashboard sync`
  - _Requirements: AC-3_

- [ ] 1.8 [GREEN] Pass test: Implement dashboard data sync via trip_list service
  - **Do**: Verify `trip_list` service in `__init__.py` returns trips from TripManager correctly
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: Test passes, service returns trips
  - **Verify**: `python3 -m pytest tests/test_dashboard.py -k "sync" -v`
  - **Commit**: `feat(dashboard): implement trip_list service sync`
  - _Requirements: AC-3_

- [ ] 1.9 [YELLOW] Refactor: Ensure trip_manager and emhass_adapter are wired correctly
  - **Do**: Check `TripManager.set_emhass_adapter()` is called during initialization, verify data flow
  - **Files**: `custom_components/ev_trip_planner/__init__.py`, `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Wiring verified
  - **Verify**: `grep -n "set_emhass_adapter" custom_components/ev_trip_planner/__init__.py`
  - **Commit**: `refactor(integration): wire TripManager to EMHASS adapter`

### AC-4: Trip State Change Updates

- [ ] 1.10 [RED] Failing test: Trip state change updates corresponding sensor
  - **Do**: Write test verifying trip state change triggers sensor update
  - **Files**: `tests/test_sensor_coverage.py`
  - **Done when**: Test exists AND fails
  - **Verify**: `python3 -m pytest tests/test_sensor_coverage.py -k "trip_state" -v 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(sensors): red - failing test for trip state updates`
  - _Requirements: AC-4_

- [ ] 1.11 [GREEN] Pass test: Implement trip state to sensor propagation
  - **Do**: In `trip_manager.py`, ensure `async_save_trip()` triggers EMHASS adapter update when trip state changes
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Trip save triggers sensor update
  - **Verify**: `python3 -m pytest tests/test_sensor_coverage.py -k "trip_state" -v`
  - **Commit**: `feat(trips): propagate state changes to sensors`
  - _Requirements: AC-4_

- [ ] 1.12 [YELLOW] Refactor: Verify schedule_monitor receives updates
  - **Do**: Check `schedule_monitor.py` properly handles trip state changes
  - **Files**: `custom_components/ev_trip_planner/schedule_monitor.py`
  - **Done when**: Update flow verified
  - **Verify**: `python3 -m pytest tests/ -k "schedule" -v`
  - **Commit**: `refactor(schedule): verify trip state update handling`

### AC-5: Error Notification Display

- [ ] 1.13 [RED] Failing test: Load errors show appropriate notification
  - **Do**: Write test verifying error notification is triggered when EMHASS load fails
  - **Files**: `tests/test_dashboard.py`
  - **Done when**: Test exists AND fails
  - **Verify**: `python3 -m pytest tests/test_dashboard.py -k "error_notification" -v 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(notifications): red - failing test for error notifications`
  - _Requirements: AC-5_

- [ ] 1.14 [GREEN] Pass test: Implement error notification on load failure
  - **Do**: In `emhass_adapter.py`, ensure error states call notification service when load fails
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Error notification triggered on failure
  - **Verify**: `python3 -m pytest tests/test_dashboard.py -k "error_notification" -v`
  - **Commit**: `feat(errors): implement error notification on load failure`
  - _Requirements: AC-5_

- [ ] 1.15 [YELLOW] Refactor: Clean up error handling paths
  - **Do**: Review all error paths in emhass_adapter and ensure consistent notification
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Error handling is consistent
  - **Verify**: `python3 -m pytest tests/ -v --tb=short`
  - **Commit**: `refactor(errors): clean up error handling paths`

- [ ] 1.16 [VERIFY] Quality checkpoint: All AC tests pass
  - **Do**: Run pytest for all integration tests
  - **Verify**: `python3 -m pytest tests/test_integration_uninstall.py tests/test_sensor_coverage.py tests/test_dashboard.py -v --tb=short`
  - **Done when**: All integration tests pass
  - **Commit**: `chore(tests): pass AC integration tests` (only if fixes needed)

## Phase 2: Additional Testing

### Integration Tests

- [ ] 2.1 Integration test: Full vehicle lifecycle (add -> trips -> delete)
  - **Do**: Create test that adds vehicle, creates trips, deletes vehicle, verifies cascade
  - **Files**: `tests/test_integration_uninstall.py`
  - **Done when**: Full lifecycle test passes
  - **Verify**: `python3 -m pytest tests/test_integration_uninstall.py -v`
  - **Commit**: `test(integration): add full vehicle lifecycle test`
  - _Requirements: AC-1, AC-2_

- [ ] 2.2 Integration test: Trip CRUD triggers EMHASS updates
  - **Do**: Create test for trip create/edit/delete and verify EMHASS sensor updates
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: CRUD triggers correct updates
  - **Verify**: `python3 -m pytest tests/test_emhass_adapter.py -v`
  - **Commit**: `test(emhass): add trip CRUD integration test`
  - _Requirements: AC-3, AC-4_

- [ ] 2.3 [VERIFY] Quality checkpoint: Integration tests pass
  - **Do**: Run full integration test suite
  - **Verify**: `python3 -m pytest tests/test_integration_uninstall.py tests/test_emhass_adapter.py -v`
  - **Done when**: All integration tests pass
  - **Commit**: `chore(tests): pass integration tests` (only if fixes needed)

## Phase 3: Quality Gates

### Local CI

- [ ] 3.1 [VERIFY] Quality check: lint, types, tests
  - **Do**: Run lint, mypy type check, and pytest
  - **Verify**: `make lint && make mypy && python3 -m pytest tests/ -v --tb=short`
  - **Done when**: Lint clean, types correct, all tests pass
  - **Commit**: `fix(qa): address lint/type issues` (if fixes needed)

- [ ] 3.2 [VERIFY] CI pipeline passes
  - **Do**: Run local CI equivalent
  - **Verify**: `pnpm run lint && pnpm test`
  - **Done when**: CI passes
  - **Commit**: None

## Phase 4: PR Lifecycle

- [ ] 4.1 Create PR and verify CI
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin feature/soc-milestone-algorithm`
    3. Create PR using gh CLI
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: PR created and CI green
  - **Commit**: None

- [ ] 4.2 Address review comments
  - **Do**: Fix any issues raised in code review
  - **Verify**: CI remains green after fixes
  - **Done when**: All comments addressed
  - **Commit**: `fix(review): address PR feedback`

## Notes

- **Integration scope**: This spec integrates fixes from US-6, US-7, US-8, US-9, US-10
- **Dependencies**: All previous specs (1-6) must be complete before this integration
- **Cascade delete**: Must clean trips, sensors, EMHASS adapter indices, persistent state
- **Sensor sync**: EmhassDeferrableLoadSensor creation/deletion synced with vehicle CRUD
- **Dashboard sync**: Data refresh on trip state changes
