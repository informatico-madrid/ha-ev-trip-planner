# Tasks: SOC Integration Baseline + Return Time Detection

## Phase 1: Implementation (POC)

### CRITICAL PREREQUISITE (Must complete before 1.1)

- [x] 0.1 [CRITICAL] Add SOC sensor to STEP_SENSORS_SCHEMA in config_flow.py
  - **Do**:
    1. Edit `config_flow.py` lines 57-70 STEP_SENSORS_SCHEMA
    2. Add `CONF_SOC_SENSOR` (already exists in `const.py:23`) as an optional entity selector in STEP_SENSORS_SCHEMA
    3. Use `selector.EntitySelector` with `domain="sensor"` to allow user to pick SOC sensor during onboarding
  - **Files**: `custom_components/ev_trip_planner/config_flow.py`
  - **Done when**: CONF_SOC_SENSOR appears in STEP_SENSORS_SCHEMA and user can select SOC sensor in config flow
  - **Verify**: `grep -n "CONF_SOC_SENSOR" custom_components/ev_trip_planner/config_flow.py`
  - **Commit**: `fix(config_flow): add SOC sensor to STEP_SENSORS_SCHEMA`
  - _Requirements: Critical prerequisite for all ACs_
  - _Design: Critical Prerequisites section (plan.md)_

### Implementation Tasks

- [x] 1.1 Add SOC change listener to PresenceMonitor
  - **Do**:
    1. Import `CONF_SOC_SENSOR` from const.py
    2. Add `soc_sensor` config attribute in `PresenceMonitor.__init__`
    3. Create `_async_setup_soc_listener()` method that registers `async_track_state_change_event` for the SOC sensor
    4. Implement `_async_handle_soc_change()` callback that:
       - Gets new SOC value from state event
       - Checks if home AND plugged (via `async_check_home_status()` and `async_check_plugged_status()`)
       - Only if home+plugged, calls `trip_manager.async_generate_power_profile()` and `trip_manager.async_generate_deferrables_schedule()`
       - **NEVER call `_publish_deferrable_loads`** (private method)
    5. Call `_async_setup_soc_listener()` at end of `__init__`
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: SOC state changes trigger recalculation calls when home and plugged
  - **Verify**: `grep -n "async_track_state_change_event" custom_components/ev_trip_planner/presence_monitor.py && grep -n "async_generate_power_profile\|async_generate_deferrables_schedule" custom_components/ev_trip_planner/presence_monitor.py`
  - **Commit**: `feat(soc): add SOC change listener to PresenceMonitor`
  - _Requirements: AC-1, AC-2, AC-3_
  - _Design: Interface Contracts section (plan.md) - trigger conditions, call async_generate_power_profile() and async_generate_deferrables_schedule()_

- [x] 1.2 Add return-time detection to PresenceMonitor
  - **Do**:
    1. Add `_was_home: bool = False` instance attribute to `PresenceMonitor.__init__`
    2. Modify `async_check_home_status()` to detect off->on transition (return home)
    3. Add `async_handle_return_home(soc_value: float)` method that:
       - Captures current timestamp using `dt_util.now()` (HomeAssistant timezone-aware datetime)
       - Stores `hora_regreso` as ISO format string
       - Stores `soc_en_regreso` as float
       - Updates the HA state entity (created in task 1.3)
    4. When return detected, call `async_handle_return_home()` with current SOC
    5. Track departure: when `home_sensor` goes off->off (was True, now False), invalidate `hora_regreso` by setting to None
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Return home (off->on) is detected and triggers handler with current SOC
  - **Verify**: `grep -n "was_home\|_was_home\|hora_regreso" custom_components/ev_trip_planner/presence_monitor.py`
  - **Commit**: `feat(presence): add return home detection`
  - _Requirements: AC-4, AC-6_
  - _Design: Return Time Detection section (plan.md)_

- [x] 1.3 Store return info using ha_storage.Store and hass.states.async_set()
  - **Do**:
    1. Add `hora_regreso` (Optional[str]) and `soc_en_regreso` (Optional[float]) instance attributes to `PresenceMonitor`
    2. Add `_return_info_store` using `ha_storage.Store` API (same pattern as trip_manager.py:95-102)
    3. Create HA state entity `sensor.ev_trip_planner_{vehicle_id}_return_info` using `hass.states.async_set()` with:
       - State: `hora_regreso` ISO string
       - Attributes JSON: `soc_en_regreso`, `hora_regreso_iso`, `vehicle_id`
    4. On each return home event, update both the Store and the state entity
    5. On departure (AC-6), clear `hora_regreso` in Store and update state entity
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Return info persisted in HA storage AND HA state entity exists with correct data
  - **Verify**: `grep -n "ha_storage.Store\|hass.states.async_set" custom_components/ev_trip_planner/presence_monitor.py`
  - **Commit**: `feat(presence): persist return time and SOC via ha_storage.Store and hass.states.async_set()`
  - _Requirements: AC-4_
  - _Design: Persistence section (plan.md) - ha_storage.Store API, hass.states.async_set() for HA state entity_

- [x] 1.4 Debounce SOC changes with 5% delta threshold (hardcoded)
  - **Do**:
    1. Add `_last_processed_soc: Optional[float] = None` attribute to `PresenceMonitor`
    2. In `_async_handle_soc_change()`, calculate: `delta = abs(new_soc - (last_processed_soc or 0))`
    3. Only trigger recalculation if `delta >= 5.0` (hardcoded, no config)
    4. Update `_last_processed_soc = new_soc` only when recalculation is triggered
    5. If SOC sensor returns unknown/unavailable, skip processing and do not update `_last_processed_soc`
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: SOC changes < 5% do not trigger recalculation; changes >= 5% do trigger
  - **Verify**: `grep -n "last_processed_soc\|5.0\|delta" custom_components/ev_trip_planner/presence_monitor.py`
  - **Commit**: `feat(soc): debounce SOC changes with hardcoded 5% threshold`
  - _Requirements: AC-2, AC-3_
  - _Design: Debouncing section (plan.md) - 5% hardcoded delta threshold_

- [ ] 1.5 Integrate SOC listener into async_setup_entry
  - **Do**:
    1. In `__init__.py:async_setup_entry()`, after PresenceMonitor creation, call `presence_monitor._async_setup_soc_listener()` if soc_sensor is configured
    2. Ensure the SOC listener is registered when the vehicle config entry is set up
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: SOC listener is active when HA starts with this vehicle
  - **Verify**: `grep -n "_async_setup_soc_listener" custom_components/ev_trip_planner/__init__.py`
  - **Commit**: `feat(soc): wire SOC listener into async_setup_entry`
  - _Requirements: AC-1_
  - _Design: Interface integration_

### POC Checkpoint

- [ ] 1.6 [VERIFY] POC verification: SOC listener triggers recalculation
  - **Do**:
    1. Start HA with test SOC sensor
    2. Verify SOC change events are tracked
    3. Verify recalculation calls are made when SOC changes >= 5% while home+plugged
  - **Done when**: SOC change listener is registered and functional
  - **Verify**: Check HA logs for "SOC change detected" messages
  - **Commit**: `chore(soc): verify POC of SOC change listener`

### Quality Checkpoints

- [ ] 1.7 [VERIFY] Quality checkpoint: lint and type check
  - **Do**: Run lint and type checks on modified files
  - **Verify**: `pylint custom_components/ev_trip_planner/presence_monitor.py custom_components/ev_trip_planner/config_flow.py && python -m mypy custom_components/ev_trip_planner/presence_monitor.py custom_components/ev_trip_planner/config_flow.py --ignore-missing-imports`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(soc): pass quality checkpoint` (only if fixes needed)
  - _Files: presence_monitor.py, config_flow.py_

- [ ] 1.8 Add unit tests for state change triggers
  - **Do**:
    1. Create `tests/test_presence_monitor_soc.py`
    2. Add test: SOC change triggers recalculation when home+plugged
    3. Add test: SOC change does NOT trigger when away or unplugged
    4. Add test: return home detection (off->on transition)
    5. Add test: SOC debouncing (5% threshold blocks recalculation)
    6. Add test: `hora_regreso`/`soc_en_regreso` persistence via Store
  - **Files**: `tests/test_presence_monitor_soc.py`
  - **Done when**: All new tests pass
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -v --tb=short 2>&1 | tail -40`
  - **Commit**: `test(soc): add unit tests for SOC change triggers`
  - _Requirements: AC-1 through AC-6_
  - _Design: Test Strategy_

## Phase 2: Verification

- [ ] 2.1 [VERIFY] Full local CI: lint && typecheck && test
  - **Do**: Run complete local CI suite
  - **Verify**: `pylint custom_components/ev_trip_planner/*.py && python -m mypy custom_components/ev_trip_planner/*.py --ignore-missing-imports && pytest tests/ -v --tb=short`
  - **Done when**: Build succeeds, all tests pass, no lint/type errors
  - **Commit**: `chore(soc): pass local CI` (only if fixes needed)

- [ ] 2.2 [VERIFY] CI pipeline passes
  - **Do**: Verify GitHub Actions/CI passes after push
  - **Verify**: `gh run list --workflow=ci.yml 2>&1 | head -10`
  - **Done when**: CI pipeline passes
  - **Commit**: None

## Notes
- POC shortcuts: Hardcoded 5% threshold, simple delta comparison, no configurable options
- Production TODOs: Consider configurable delta threshold, more sophisticated debouncing algorithm
- Dependencies: Task 0.1 (config_flow) must complete before 1.1 (SOC listener)
- Call patterns: MUST call `async_generate_power_profile()` and `async_generate_deferrables_schedule()`, NEVER `_publish_deferrable_loads`
- Persistence: Uses `ha_storage.Store` API same as trip_manager.py L95-102
- State entity: Uses `hass.states.async_set()` for `sensor.ev_trip_planner_{vehicle_id}_return_info`
- Datetime: Uses `dt_util.now()` for timezone-aware HomeAssistant datetime
