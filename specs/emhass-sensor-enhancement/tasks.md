# Tasks: EMHASS Sensor Enhancement

## Phase 1: Make It Work (POC)

Focus: Validate the sensor enhancement works end-to-end. Skip tests initially, accept hardcoded values.

- [x] 1.1 [P] Add last_update and emhass_status attributes to EmhassDeferrableLoadSensor
  - **Do**:
    1. Open `custom_components/ev_trip_planner/sensor.py`
    2. In `EmhassDeferrableLoadSensor.__init__()`, add `_index_cooldown_hours: int = 24` attribute
    3. In `EmhassDeferrableLoadSensor.async_update()`, add `last_update` and `emhass_status` to `self._cached_attrs`
    4. Set `last_update` to ISO format timestamp of current time
    5. Set `emhass_status` to "ok" on success, "error" on failure
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: EmhassDeferrableLoadSensor extra_state_attributes includes last_update and emhass_status
  - **Verify**: `grep -n "last_update\|emhass_status" custom_components/ev_trip_planner/sensor.py | head -20`
  - **Commit**: `feat(sensor): add last_update and emhass_status to EmhassDeferrableLoadSensor`
  - _Requirements: AC-3, AC-5_
  - _Design: Interface Contracts_

- [x] 1.2 [P] Add soft delete mechanism to EMHASSAdapter
  - **Do**:
    1. Open `custom_components/ev_trip_planner/emhass_adapter.py`
    2. In `__init__()`, add `self._released_indices: Dict[int, datetime] = {}` and `self._index_cooldown_hours: int = 24`
    3. Modify `async_release_trip_index()` to store released index in `_released_indices` with timestamp instead of adding to `_available_indices`
    4. Modify `async_assign_index_to_trip()` to use `get_available_indices()` method instead of directly accessing `_available_indices`
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Released indices go to _released_indices dict, not _available_indices
  - **Verify**: `grep -n "_released_indices" custom_components/ev_trip_planner/emhass_adapter.py | head -10`
  - **Commit**: `feat(emhass): add soft delete for released indices`
  - _Requirements: AC-2_
  - _Design: Index Stability (Soft Delete)_

- [x] 1.3 [P] Add get_available_indices method with cooldown logic
  - **Do**:
    1. In `emhass_adapter.py`, add `get_available_indices()` method that:
       - Checks `_released_indices` for indices past cooldown
       - Moves expired indices from `_released_indices` to `_available_indices`
       - Returns combined list of available + newly expired indices
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: get_available_indices() returns only indices past 24h cooldown
  - **Verify**: `grep -n "def get_available_indices" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `feat(emhass): add get_available_indices with cooldown logic`
  - _Requirements: AC-2_
  - _Design: Index Stability (Soft Delete)_

- [x] 1.4 [P] Update async_update in sensor to include trips_count and vehicle_id
  - **Do**:
    1. In `EmhassDeferrableLoadSensor.async_update()`, after generating schedule, add:
       - `trips_count` to cached_attrs (from len of active trips)
       - `vehicle_id` to cached_attrs (from trip_manager.vehicle_id)
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Sensor attributes include trips_count and vehicle_id
  - **Verify**: `grep -n "trips_count\|vehicle_id" custom_components/ev_trip_planner/sensor.py`
  - **Commit**: `feat(sensor): add trips_count and vehicle_id to sensor attributes`
  - _Requirements: AC-1, AC-4_
  - _Design: Interface Contracts_

- [x] 1.5 [VERIFY] Quality checkpoint: POC builds and basic functionality works
  - **Do**: Run lint and type check on modified files
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && ruff check custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/emhass_adapter.py && echo PASS`
  - **Done when**: No lint errors, code compiles
  - **Commit**: `chore: pass POC quality checkpoint`

- [x] 1.6 POC Checkpoint: Verify sensor has correct attributes format
  - **Do**: Run targeted tests to verify sensor attributes format
  - **Done when**: Sensor state returns "ready" | "error", attributes include power_profile_watts (168 values), deferrables_schedule, trips_count, vehicle_id, last_update, emhass_status
  - **Verify**: `python3 -m pytest tests/test_deferrable_load_sensors.py -v --tb=short -k "test_sensor_initial_state or test_sensor_updates_attributes" 2>&1 | tail -20`
  - **Commit**: `feat(sensor): POC checkpoint verified`

## Phase 2: Refactoring

After POC validated, clean up code structure.

- [x] 2.1 Extract EMHASS status constants
  - **Do**:
    1. Create constants for EMHASS states in `const.py`: `EMHASS_STATE_READY = "ready"`, `EMHASS_STATE_ACTIVE = "active"`, `EMHASS_STATE_ERROR = "error"`
    2. Import and use these constants in `sensor.py` and `emhass_adapter.py`
  - **Files**: custom_components/ev_trip_planner/const.py, custom_components/ev_trip_planner/sensor.py, custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Constants used instead of string literals
  - **Verify**: `grep -n "EMHASS_STATE" custom_components/ev_trip_planner/const.py custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `refactor(emhass): extract EMHASS state constants`
  - _Design: Architecture_

- [x] 2.2 Add index cooldown configuration to config flow
  - **Do**:
    1. Add `CONF_INDEX_COOLDOWN_HOURS` to const.py with default value 24
    2. Add cooldown hours field to config flow schema
    3. Pass cooldown hours to EMHASSAdapter constructor
  - **Files**: custom_components/ev_trip_planner/const.py, custom_components/ev_trip_planner/config_flow.py, custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Cooldown is configurable via config flow
  - **Verify**: `grep -n "cooldown" custom_components/ev_trip_planner/config_flow.py custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `feat(config): add index cooldown configuration`
  - _Design: Soft Delete Algorithm_

- [x] 2.3 [VERIFY] Quality checkpoint: refactored code passes checks
  - **Do**: Run quality checks on refactored code
  - **Verify**: `make lint && make mypy 2>&1 | tail -30`
  - **Done when**: All lint and type checks pass
  - **Commit**: `chore: pass refactoring quality checkpoint`

## Phase 3: Testing

- [x] 3.1 Add unit tests for soft delete index stability
  - **Do**:
    1. Create test file `tests/test_emhass_soft_delete.py`
    2. Add tests:
       - `test_released_index_not_immediately_available()` - verify released index goes to _released_indices
       - `test_released_index_available_after_cooldown()` - verify index moves after cooldown expires
       - `test_new_trip_gets_next_available_index()` - verify new trips don't reuse released indices
       - `test_multiple_indicesReleased_cooldown_handled_correctly()` - verify independent cooldown timers
  - **Files**: tests/test_emhass_soft_delete.py
  - **Done when**: Tests cover soft delete behavior
  - **Verify**: `python3 -m pytest tests/test_emhass_soft_delete.py -v --tb=short 2>&1 | tail -30`
  - **Commit**: `test(emhass): add unit tests for soft delete index stability`
  - _Requirements: AC-2_
  - _Design: Index Stability_

- [x] 3.2 Add tests for sensor last_update and emhass_status attributes
  - **Do**:
    1. Add tests to `tests/test_deferrable_load_sensors.py`:
       - `test_sensor_includes_last_update_attribute()` - verify last_update timestamp present
       - `test_sensor_includes_emhass_status_attribute()` - verify emhass_status present
       - `test_sensor_emhass_status_error_on_exception()` - verify status set to error on failure
  - **Files**: tests/test_deferrable_load_sensors.py
  - **Done when**: New sensor attributes are tested
  - **Verify**: `python3 -m pytest tests/test_deferrable_load_sensors.py -v --tb=short -k "last_update or emhass_status" 2>&1 | tail -20`
  - **Commit**: `test(sensor): add tests for last_update and emhass_status`
  - _Requirements: AC-3, AC-5_
  - _Design: Interface Contracts_

- [x] 3.3 Add integration test for deferrables_schedule p_deferrable{n} per hour
  - **Do**:
    1. Add test to `tests/test_deferrables_schedule.py`:
       - `test_schedule_shows_p_deferrable_per_hour()` - verify schedule entries contain p_deferrable{n} keys
  - **Files**: tests/test_deferrables_schedule.py
  - **Done when**: Schedule format is validated
  - **Verify**: `python3 -m pytest tests/test_deferrables_schedule.py -v --tb=short -k "p_deferrable" 2>&1 | tail -20`
  - **Commit**: `test(schedule): add tests for p_deferrable per hour format`
  - _Requirements: AC-4, AC-5_
  - _Design: Interface Contracts_

- [x] 3.4 Add test for multiple trips with correct p_deferrable indices
  - **Do**:
    1. Add test `test_multiple_trips_assigned_sequential_indices()` to verify 3 trips get p_deferrable0, p_deferrable1, p_deferrable2
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: AC-1 satisfied by test
  - **Verify**: `python3 -m pytest tests/test_emhass_adapter.py -v --tb=short -k "multiple" 2>&1 | tail -20`
  - **Commit**: `test(emhass): add test for multiple trips with sequential indices`
  - _Requirements: AC-1_
  - _Design: Interface Contracts_

- [x] 3.5 [VERIFY] Quality checkpoint: all tests pass
  - **Do**: Run full test suite
  - **Verify**: `make test 2>&1 | tail -40`
  - **Done when**: All tests pass
  - **Commit**: `chore: pass testing quality checkpoint`

## Phase 4: Quality Gates

- [x] 4.1 Local quality check
  - **Do**: Run ALL quality checks locally
  - **Verify**: All commands must pass:
    - Type check: `make mypy`
    - Lint: `make lint`
    - Tests: `make test`
  - **Done when**: All commands pass with no errors
  - **Commit**: `fix: address lint/type issues` (if fixes needed)

- [x] 4.2 Create PR and verify CI
  - **Do**:
    1. Verify current branch is a feature branch: `git branch --show-current`
    2. If on default branch, STOP and alert user (should not happen - branch is set at startup)
    3. Push branch: `git push -u origin <branch-name>`
    4. Create PR using gh CLI: `gh pr create --title "feat(emhass): enhance sensor with stable indices" --body "$(cat <<'EOF'
## Summary
- Add last_update and emhass_status attributes to EmhassDeferrableLoadSensor
- Implement soft delete for EMHASS indices with 24h cooldown
- Add get_available_indices() method with cooldown reclamation
- Wire sensor updates to trip add/modify/delete handlers

## Test plan
- [x] Unit tests for soft delete index stability (tests/test_emhass_soft_delete.py - 4 tests)
- [x] Unit tests for last_update and emhass_status attributes (tests/test_deferrable_load_sensors.py - 3 tests)
- [x] Integration tests for deferrables_schedule p_deferrable{n} format (tests/test_deferrable_load_sensors.py)
- [x] Multiple trips assigned sequential indices test (tests/test_emhass_adapter.py::test_multiple_trips_assigned_sequential_indices)
- [x] All existing tests pass (80 tests in emhass adapter/sensor tests)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"`
  - **Verify**: Use gh CLI to verify CI:
    - `gh pr checks --watch` (wait for CI completion)
    - Or `gh pr checks` (poll current status)
    - All checks must show pass
  - **Done when**: All CI checks green, PR ready for review
  - **If CI fails**:
    1. Read failure details: `gh pr checks`
    2. Fix issues locally
    3. Push fixes: `git push`
    4. Re-verify: `gh pr checks --watch`

## Phase 5: PR Lifecycle

- [x] 5.1 Monitor CI pipeline
  - **Do**: Watch PR checks and address any failures
  - **Verify**: `gh pr checks` shows all passing
  - **Done when**: All CI checks green

- [x] 5.2 Address code review comments
  - **Do**: Respond to and resolve any review feedback
  - **Verify**: All comments resolved, CI still passing
  - **Done when**: PR approved

- [x] 5.3 Final verification
  - **Do**:
    1. Re-run full test suite: `make test`
    2. Verify lint: `make lint`
    3. Verify types: `make mypy`
  - **Verify**: All commands exit 0
  - **Done when**: All checks pass, PR merged or approved

## Notes

**POC shortcuts taken**:
- Hardcoded 24h cooldown initially (made configurable in Phase 2)
- Sensor attributes set directly without validation (validated in Phase 3)

**Production TODOs**:
- Add config flow field for index_cooldown_hours
- Add UI for viewing released indices status
- Consider adding admin endpoint to force-reclaim an index
- Add monitoring/alerting when approaching max indices limit

## Learnings

- Task planning insight: EMHASSAdapter manages index lifecycle, sensor just displays data
- Dependency discovered: sensor update relies on trip_manager.async_generate_* methods existing
- Verification commands: Use `make test`, `make lint`, `make mypy` from Makefile
