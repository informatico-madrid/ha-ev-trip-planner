# Tasks: m401-emhass-hotfixes

## Phase 1: TDD Cycles — Gap #5 Hotfixes

Focus: Fix 3 root causes for charging power updates being silently ignored. Each fix starts with a failing test.

- [ ] 1.1 [RED] Failing test: `update_charging_power` reads `entry.options` first
  - **Do**:
    1. In `tests/test_emhass_adapter.py`, write test `test_update_charging_power_reads_options_first` that creates `MockConfigEntry` with `options={"charging_power_kw": 3.6}`, `data={"charging_power_kw": 11}`
    2. Assert adapter reads 3.6 (options) not 11 (data)
    3. Test must fail because current code reads `entry.data` only
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test exists AND fails — `entry.data.get("charging_power_kw")` returns 11, not 3.6
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_update_charging_power_reads_options_first" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for options-first read`
  - _Requirements: FR-1, AC-1.1_

- [ ] 1.2 [GREEN] Fix `update_charging_power` to read `entry.options` first, fallback `entry.data`
  - **Do**:
    1. In `emhass_adapter.py:1359`, change to use `is None` check (NOT `or`) to correctly handle `charging_power_kw=0` edge case:
       ```python
       new_power = entry.options.get("charging_power_kw")
       if new_power is None:
           new_power = entry.data.get("charging_power_kw")
       ```
       Note: `or` would treat `0` as falsy and fall through — `is None` is correct.
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Previously failing test passes — reads 3.6 from options
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_update_charging_power_reads_options_first"`
  - **Commit**: `fix(emhass): read charging_power_kw from options first, fallback data`
  - _Requirements: FR-1, AC-1.1_

- [x] 1.3 [GREEN] Verify data fallback path works — write and run fallback test
  - **Do**:
    1. Write test `test_update_charging_power_fallback_to_data` with `options={}` (no charging_power_kw), `data={"charging_power_kw": 11}`
    2. Assert adapter reads 11 from data fallback
    3. Note: This is NOT [RED] — the fallback path works with both old and new code since `options.get()` returns `None` and `is None` check falls through to `data.get()`
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Fallback test passes — reads 11 from data when options is empty
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_update_charging_power_fallback_to_data"`
  - **Commit**: `test(emhass): green - verify data fallback for charging power`

- [x] 1.4 [GREEN] Test edge case: `charging_power_kw=0` is not treated as falsy
  - **Do**:
    1. Write test `test_update_charging_power_zero_not_falsy` with `options={"charging_power_kw": 0}`, `data={"charging_power_kw": 11}`
    2. Assert adapter reads 0 from options (NOT falling through to data's 11)
    3. This validates the `is None` check — `or` would incorrectly treat 0 as falsy
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test passes — `charging_power_kw=0` correctly read from options, not replaced by data fallback
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_update_charging_power_zero_not_falsy"`
  - **Commit**: `test(emhass): verify charging_power_kw=0 edge case for is None check`
  - _Requirements: FR-1, NFR-1_

- [x] 1.5 [RED] Failing test: `setup_config_entry_listener` is called in `async_setup_entry`
  - **Do**:
    1. In `tests/test_init.py`, write test `test_listener_activated_in_setup` that mocks EMHASSAdapter and verifies `setup_config_entry_listener()` is called after adapter creation in `async_setup_entry`
    2. Assert mock method was called once
    3. Note: Test goes in `test_init.py` because `async_setup_entry` lives in `__init__.py`, not `emhass_adapter.py`
  - **Files**: tests/test_init.py
  - **Done when**: Test exists AND fails — listener activation not yet added to `__init__.py`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_init.py -x -k "test_listener_activated_in_setup" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(init): red - failing test for listener activation in setup`
  - _Requirements: FR-2, AC-1.2_

- [x] 1.6 [GREEN] Activate `setup_config_entry_listener()` in `__init__.py`
  - **Do**:
    1. In `__init__.py`, after `await emhass_adapter.async_load()` (~line 119), add `emhass_adapter.setup_config_entry_listener()`
  - **Files**: custom_components/ev_trip_planner/__init__.py
  - **Done when**: Test passes — `setup_config_entry_listener` called during setup
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_init.py -x -k "test_listener_activated_in_setup"`
  - **Commit**: `feat(init): activate config entry listener for charging power updates`
  - _Requirements: FR-2, AC-1.2_

- [x] 1.7 [RED] Failing test: empty `_published_trips` guard reloads from trip_manager
  - **Do**:
    1. Write test `test_empty_published_trips_guard` with adapter where `_published_trips=[]`, mock coordinator with trip_manager that has trips
    2. Assert trips are reloaded before republish
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test exists AND fails — guard not yet implemented in `_handle_config_entry_update`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_empty_published_trips_guard" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for empty published trips guard`
  - _Requirements: FR-3, AC-1.3_

- [x] 1.8 [GREEN] Add empty `_published_trips` guard in `_handle_config_entry_update`
  - **Do**:
    1. In `_handle_config_entry_update` (emhass_adapter.py:1334), before `await self.update_charging_power()`:
       - If `not self._published_trips`, get coordinator, get trip_manager
       - Load `recurring_trips` + `punctual_trips` into `self._published_trips`
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Test passes — trips reloaded when `_published_trips` is empty
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_empty_published_trips_guard"`
  - **Commit**: `fix(emhass): reload trips from trip_manager when _published_trips is empty`
  - _Requirements: FR-3, AC-1.3_

- [x] V1 [VERIFY] Quality checkpoint: Gap #5 hotfixes
  - **Do**: Run quality commands
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x && ruff check custom_components/ev_trip_planner/emhass_adapter.py custom_components/ev_trip_planner/__init__.py && mypy custom_components/ev_trip_planner/emhass_adapter.py custom_components/ev_trip_planner/__init__.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(emhass): pass quality checkpoint after gap-5 hotfixes`

## Phase 1 (continued): TDD Cycles — Per-Trip Params Cache

Focus: Add per-trip EMHASS param caching infrastructure. Each helper starts with a failing test.

Note: No new `_calculate_individual_power_profile` method needed — the existing `_calculate_power_profile_from_trips([trip], power)` already does exactly this. Per-trip caching uses it directly.

- [ ] 1.9 [RED] Failing test: `_get_current_soc` reads from configured sensor
  - **Do**:
    1. Write test `test_get_current_soc_reads_sensor` with mock `hass.states.get` returning state with `state="65.0"`
    2. Assert returns 65.0
    3. Write test `test_get_current_soc_sensor_unavailable` returning None, assert returns 0.0
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Tests exist AND fail — method does not exist yet
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_get_current_soc" 2>&1 | grep -qi "fail\|error\|attribute" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for _get_current_soc helper`
  - _Design: Component 1_

- [ ] 1.10 [GREEN] Add `_get_current_soc` helper
  - **Do**:
    1. Add method that reads `self._entry.data.get("soc_sensor")` then `self.hass.states.get(soc_sensor)`
    2. Parse float, return 0.0 if unavailable/unparseable
    3. Note: use `self.hass` (NOT `self._hass`) per emhass_adapter.py:43
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Both SOC tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_get_current_soc"`
  - **Commit**: `feat(emhass): add _get_current_soc helper for sensor SOC reads`
  - _Design: Component 1_

- [ ] 1.11 [RED] Failing test: `_get_hora_regreso` returns datetime from presence_monitor
  - **Do**:
    1. Write test `test_get_hora_regreso_success` with mock coordinator chain returning a datetime
    2. Write test `test_get_hora_regreso_no_coordinator` returning None
    3. Assert correct values
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Tests exist AND fail — method does not exist yet
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_get_hora_regreso" 2>&1 | grep -qi "fail\|error\|attribute" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for _get_hora_regreso helper`
  - _Design: Component 1_

- [ ] 1.12 [GREEN] Add `_get_hora_regreso` async helper
  - **Do**:
    1. Add async method that traverses `coordinator._trip_manager.vehicle_controller._presence_monitor.async_get_hora_regreso()`
    2. Return None if any link in chain is missing
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Both hora_regreso tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_get_hora_regreso"`
  - **Commit**: `feat(emhass): add _get_hora_regreso helper for presence monitor chain`
  - _Design: Component 1_

- [ ] 1.13 [RED] Failing test: `async_publish_deferrable_load` computes `def_start_timestep` from charging windows
  - **Do**:
    1. Write test `test_publish_deferrable_load_computes_start_timestep` with a trip that should have start_timestep > 0 (e.g., second trip with later window)
    2. Mock `_get_current_soc` returning 50.0, `_get_hora_regreso` returning a datetime
    3. Assert `def_start_timestep` != 0 for the second trip
    4. **IMPORTANT**: Use `freezegun` (`@freeze_time("2026-04-11 12:00:00")`) or mock `datetime.now()` to make test deterministic — the conversion `(inicio_ventana - now).total_seconds() / 3600` depends on current time
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test exists AND fails — `def_start_timestep` still hardcoded to 0
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_publish_deferrable_load_computes_start_timestep" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for computed def_start_timestep`
  - _Requirements: FR-9c_

- [ ] 1.14 [GREEN] Fix `def_start_timestep` in `async_publish_deferrable_load` to use charging windows
  - **Do**:
    1. Import `calculate_multi_trip_charging_windows` from calculations.py
    2. In `async_publish_deferrable_load`, call `self._get_current_soc()` and `await self._get_hora_regreso()`
    3. Call `calculate_multi_trip_charging_windows()` with single trip, SOC, hora_regreso
    4. Convert `inicio_ventana` (datetime) to timestep: `max(0, min(int((inicio_ventana - now).total_seconds() / 3600), 168))`
    5. Replace hardcoded `def_start_timestep: 0` with computed value
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Test passes — `def_start_timestep` is computed, not hardcoded 0
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_publish_deferrable_load_computes_start_timestep"`
  - **Commit**: `fix(emhass): compute def_start_timestep from charging windows instead of hardcoding 0`
  - _Requirements: FR-9c_

- [ ] 1.15 [RED] Failing test: `publish_deferrable_loads` caches per-trip params
  - **Do**:
    1. Write test `test_publish_deferrable_loads_caches_per_trip_params` with 2 trips
    2. Assert `_cached_per_trip_params` populated with trip_id keys containing `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `power_profile_watts`, `trip_id`, `emhass_index`, `kwh_needed`, `deadline`, `activo`
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test exists AND fails — `_cached_per_trip_params` not yet populated
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_publish_deferrable_loads_caches_per_trip" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for per-trip params caching`
  - _Design: Component 1_

- [x] 1.16 [GREEN] Cache per-trip params in `publish_deferrable_loads`
  - **Do**:
    1. Add `_cached_per_trip_params: Dict[str, dict]` instance variable (init as `{}`)
    2. After enrichment loop in `publish_deferrable_loads`, iterate trips with index_map entries
    3. For each trip in `_index_map`, compute params via `calculate_deferrable_parameters` + `self._calculate_power_profile_from_trips([trip], charging_power_kw)`
    4. Store in `_cached_per_trip_params[trip_id]` with all 10 keys
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Test passes — `_cached_per_trip_params` populated correctly
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_publish_deferrable_loads_caches_per_trip"`
  - **Commit**: `feat(emhass): cache per-trip EMHASS params in publish_deferrable_loads`
  - _Design: Component 1_

- [x] V2 [VERIFY] Quality checkpoint: per-trip params cache
  - **Do**: Run quality commands
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x && ruff check custom_components/ev_trip_planner/emhass_adapter.py && mypy custom_components/ev_trip_planner/emhass_adapter.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(emhass): pass quality checkpoint after per-trip params cache`

- [x] 1.17 [RED] Failing test: `get_cached_optimization_results` includes `per_trip_emhass_params`
  - **Do**:
    1. Write test `test_get_cached_results_includes_per_trip_params` that populates `_cached_per_trip_params` then calls `get_cached_optimization_results()`
    2. Assert returned dict has key `per_trip_emhass_params` with same data
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test exists AND fails — key not yet added to return dict
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_get_cached_results_includes_per_trip" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for per_trip_emhass_params in cached results`
  - _Design: Component 1_

- [x] 1.18 [GREEN] Add `per_trip_emhass_params` to `get_cached_optimization_results`
  - **Do**:
    1. In `get_cached_optimization_results()`, add `"per_trip_emhass_params": self._cached_per_trip_params` to returned dict
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Test passes — `per_trip_emhass_params` key present in cached results
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_get_cached_results_includes_per_trip"`
  - **Commit**: `feat(emhass): include per_trip_emhass_params in cached optimization results`
  - _Design: Component 1_

- [x] 1.19 [RED/GREEN] inicio_ventana to timestep conversion edge cases
  - **Do**: Tests pass because 1.16 implementation already has correct clamping
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_inicio_ventana"`
  - **Commit**: `test(emhass): edge case tests for timestep conversion (already passing)`

- [ ] 1.20 [SKIP] No code change needed — clamping already correct
  - **Note**: Task 1.19 tests pass because implementation already clamps to [0, 168] range

- [ ] V3 [VERIFY] Quality checkpoint: per-trip cache + timestep conversion
  - **Do**: Run full adapter test suite + lint + typecheck
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x && ruff check custom_components/ev_trip_planner/emhass_adapter.py && mypy custom_components/ev_trip_planner/emhass_adapter.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(emhass): pass quality checkpoint after cache + timestep fixes`

## Phase 1 (continued): TDD Cycles — TripEmhassSensor

Focus: New per-trip EMHASS sensor class with 9 attributes. Tests go in `tests/test_trip_emhass_sensor.py` (SRP — separate from existing sensor tests).

- [ ] 1.23 [RED] Failing test: `TripEmhassSensor.native_value` returns emhass_index
  - **Do**:
    1. In `tests/test_trip_emhass_sensor.py`, write test `test_trip_emhass_sensor_native_value` with stub coordinator.data containing `per_trip_emhass_params` with trip having `emhass_index=2`
    2. Assert `sensor.native_value == 2`
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails — `TripEmhassSensor` class does not exist yet
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_native_value" 2>&1 | grep -qi "fail\|error\|import\|attribute" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for TripEmhassSensor native_value`
  - _Requirements: FR-4, AC-2.1_

- [ ] 1.24 [GREEN] Create `TripEmhassSensor` class with `native_value`
  - **Do**:
    1. In `sensor.py`, add `TripEmhassSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity)`
    2. `__init__(coordinator, vehicle_id, trip_id)` — set `_attr_unique_id = f"emhass_trip_{vehicle_id}_{trip_id}"`
    3. `native_value` property reads `coordinator.data["per_trip_emhass_params"][trip_id]["emhass_index"]`, returns -1 if not found
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — `native_value == 2`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_native_value"`
  - **Commit**: `feat(sensor): create TripEmhassSensor class with native_value`
  - _Requirements: FR-4, AC-2.1, AC-2.5_

- [ ] 1.25 [RED] Failing test: `TripEmhassSensor.extra_state_attributes` returns 9 attributes
  - **Do**:
    1. Write test `test_trip_emhass_sensor_attributes_all_9` with full params dict
    2. Assert attrs dict has keys: `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `power_profile_watts`, `trip_id`, `emhass_index`, `kwh_needed`, `deadline`
    3. Assert `power_profile_watts` is list of 168 elements
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails — `extra_state_attributes` not yet implemented
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_attributes_all_9" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for TripEmhassSensor 9 attributes`
  - _Requirements: FR-4, AC-2.2_

- [ ] 1.26 [GREEN] Implement `TripEmhassSensor.extra_state_attributes` with 9 attributes
  - **Do**:
    1. Add `_get_params()` helper — reads `coordinator.data["per_trip_emhass_params"][self._trip_id]`
    2. Add `_zeroed_attributes()` — returns all 9 attrs with zeroed values
    3. `extra_state_attributes` — returns params if available, else zeroed
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — all 9 attrs present with correct values
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_attributes_all_9"`
  - **Commit**: `feat(sensor): implement TripEmhassSensor extra_state_attributes with 9 attrs`
  - _Requirements: FR-4, AC-2.2_

- [ ] 1.27 [RED] Failing test: `TripEmhassSensor` returns zeroed attributes when no params
  - **Do**:
    1. Write test `test_trip_emhass_sensor_zeroed_when_no_params` with coordinator.data=None
    2. Assert all attrs are zeroed: `power_profile_watts` all zeros, `def_total_hours=0`, `P_deferrable_nom=0`
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails (or passes if 1.26 already handles this)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_zeroed" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS || echo GREEN_PASS`
  - **Commit**: `test(sensor): red - failing test for TripEmhassSensor zeroed fallback`

- [ ] 1.28 [GREEN] Verify zeroed fallback (may already pass from 1.26)
  - **Do**:
    1. Run test — if it passes from 1.26's `_zeroed_attributes()` path, no code change
    2. If it fails, ensure `_get_params()` returns None when coordinator.data is None
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Zeroed fallback test passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_zeroed"`
  - **Commit**: `fix(sensor): ensure TripEmhassSensor returns zeroed attrs when no params`
  - _Requirements: FR-7, AC-2.4_

- [ ] 1.29 [RED] Failing test: `TripEmhassSensor.device_info` uses vehicle_id identifiers
  - **Do**:
    1. Write test `test_trip_emhass_sensor_device_info` asserting `identifiers={(DOMAIN, vehicle_id)}`
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails — `device_info` not yet implemented
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_device_info" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for TripEmhassSensor device_info`
  - _Requirements: AC-2.6_

- [ ] 1.30 [GREEN] Implement `TripEmhassSensor.device_info`
  - **Do**:
    1. Add `device_info` property returning `{identifiers={(DOMAIN, self._vehicle_id)}, ...}` — matches `EmhassDeferrableLoadSensor.device_info` pattern
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — correct device identifiers
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_trip_emhass_sensor_device_info"`
  - **Commit**: `feat(sensor): implement TripEmhassSensor device_info with vehicle_id`
  - _Requirements: AC-2.6_

- [ ] V4a [VERIFY] Quality checkpoint: TripEmhassSensor class
  - **Do**: Run quality commands
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x && ruff check custom_components/ev_trip_planner/sensor.py && mypy custom_components/ev_trip_planner/sensor.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(sensor): pass quality checkpoint after TripEmhassSensor`

## Phase 1 (continued): TDD Cycles — Sensor CRUD Functions

Focus: Add EMHASS sensor create/remove functions.

- [ ] 1.31 [RED] Failing test: `async_create_trip_emhass_sensor` calls `async_add_entities`
  - **Do**:
    1. Write test `test_create_trip_emhass_sensor_success` with mock `runtime_data` containing `sensor_async_add_entities` callback
    2. Assert callback called with list containing TripEmhassSensor instance
    3. Assert returns True
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails — function does not exist yet
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_create_trip_emhass_sensor_success" 2>&1 | grep -qi "fail\|error\|import\|attribute" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for async_create_trip_emhass_sensor`
  - _Requirements: FR-5_

- [ ] 1.32 [GREEN] Implement `async_create_trip_emhass_sensor`
  - **Do**:
    1. Add module-level function in sensor.py mirroring `async_create_trip_sensor` pattern
    2. Get entry, runtime_data, coordinator, `sensor_async_add_entities`
    3. Create `TripEmhassSensor(coordinator, vehicle_id, trip_id)`, call `async_add_entities([sensor], True)`
    4. Return True on success, False on failure
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — callback called with TripEmhassSensor
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_create_trip_emhass_sensor_success"`
  - **Commit**: `feat(sensor): implement async_create_trip_emhass_sensor`
  - _Requirements: FR-5_

- [ ] 1.33 [RED] Failing test: `async_create_trip_emhass_sensor` returns False when no entry
  - **Do**:
    1. Write test `test_create_trip_emhass_sensor_no_entry` with hass returning None for entry
    2. Assert returns False, no callback called
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails (or passes from 1.32's guard)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_create_trip_emhass_sensor_no_entry" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS || echo GREEN_PASS`
  - **Commit**: `test(sensor): red - failing test for create EMHASS sensor no entry`

- [ ] 1.34 [GREEN] Verify no-entry guard in `async_create_trip_emhass_sensor`
  - **Do**: Run test — should already pass from 1.32's entry lookup guard
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — returns False when entry is None
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_create_trip_emhass_sensor_no_entry"`
  - **Commit**: `test(sensor): green - verify create EMHASS sensor returns False on no entry`

- [ ] 1.35 [RED] Failing test: `async_remove_trip_emhass_sensor` removes from entity registry
  - **Do**:
    1. Write test `test_remove_trip_emhass_sensor_success` with mock entity_registry containing matching entry
    2. Assert `registry.async_remove` called with correct entity_id
    3. Assert returns True
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails — function does not exist yet
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_remove_trip_emhass_sensor_success" 2>&1 | grep -qi "fail\|error\|import\|attribute" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for async_remove_trip_emhass_sensor`
  - _Requirements: FR-6_

- [ ] 1.36 [GREEN] Implement `async_remove_trip_emhass_sensor`
  - **Do**:
    1. Add module-level function in sensor.py mirroring `async_remove_trip_sensor` pattern
    2. Get entity_registry, find entries for config_entry_id containing `trip_id` in unique_id AND containing `emhass_trip` prefix
    3. Call `registry.async_remove(entity_id)`, return True
    4. Return False if not found
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — registry removal called
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_remove_trip_emhass_sensor_success"`
  - **Commit**: `feat(sensor): implement async_remove_trip_emhass_sensor`
  - _Requirements: FR-6_

- [ ] 1.37 [RED] Failing test: `async_remove_trip_emhass_sensor` returns False when not found
  - **Do**:
    1. Write test `test_remove_trip_emhass_sensor_not_found` with empty entity_registry
    2. Assert returns False, no removal attempted
  - **Files**: tests/test_trip_emhass_sensor.py
  - **Done when**: Test exists AND fails (or passes from 1.36's guard)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_remove_trip_emhass_sensor_not_found" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS || echo GREEN_PASS`
  - **Commit**: `test(sensor): red - failing test for remove EMHASS sensor not found`

- [ ] 1.38 [GREEN] Verify not-found guard in `async_remove_trip_emhass_sensor`
  - **Do**: Run test — should already pass from 1.36's not-found guard
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — returns False when sensor not found in registry
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x -k "test_remove_trip_emhass_sensor_not_found"`
  - **Commit**: `test(sensor): green - verify remove EMHASS sensor returns False on not found`

- [ ] V4b [VERIFY] Quality checkpoint: sensor CRUD functions
  - **Do**: Run quality commands
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_emhass_sensor.py -x && ruff check custom_components/ev_trip_planner/sensor.py && mypy custom_components/ev_trip_planner/sensor.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(sensor): pass quality checkpoint after EMHASS sensor CRUD`

## Phase 1 (continued): TDD Cycles — Aggregated Sensor Extensions

Focus: Add 6 new array/matrix attributes to `EmhassDeferrableLoadSensor`.

- [ ] 1.39 [RED] Failing test: `EmhassDeferrableLoadSensor` includes `p_deferrable_matrix` attribute
  - **Do**:
    1. Write test `test_aggregated_sensor_matrix` with stub coordinator.data containing `per_trip_emhass_params` with 2 active trips
    2. Assert `extra_state_attributes["p_deferrable_matrix"]` is `list[list[float]]` with 2 rows of 168 elements
  - **Files**: tests/test_sensor_coverage.py
  - **Done when**: Test exists AND fails — matrix not yet added to `extra_state_attributes`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_matrix" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for p_deferrable_matrix attribute`
  - _Requirements: FR-8, AC-3.1, AC-3.2_

- [ ] 1.40 [GREEN] Extend `EmhassDeferrableLoadSensor.extra_state_attributes` with 6 new attrs
  - **Do**:
    1. Add `_get_active_trips_ordered(per_trip)` helper — filter `activo=True`, sort by `emhass_index` ascending
    2. In `extra_state_attributes`, after existing attrs, build 6 new attrs from sorted active trips:
       - `p_deferrable_matrix`, `number_of_deferrable_loads`, `def_total_hours_array`, `p_deferrable_nom_array`, `def_start_timestep_array`, `def_end_timestep_array`
    3. Merge with existing attrs dict
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — matrix is list of 2 lists with 168 elements each
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_matrix"`
  - **Commit**: `feat(sensor): add 6 EMHASS array/matrix attributes to aggregated sensor`
  - _Requirements: FR-8, FR-9, FR-9a-d, AC-3.1-3.5_

- [ ] 1.41 [RED] Failing test: aggregated sensor arrays have matching lengths
  - **Do**:
    1. Write test `test_aggregated_sensor_array_lengths_match` — verify all 5 array attrs + matrix rows have same length as `number_of_deferrable_loads`
  - **Files**: tests/test_sensor_coverage.py
  - **Done when**: Test exists AND fails (or passes if 1.40 already guarantees this)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_array_lengths" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS || echo GREEN_PASS`
  - **Commit**: `test(sensor): red - failing test for array length consistency`

- [ ] 1.42 [GREEN] Verify array length consistency
  - **Do**: Run test — should pass from 1.40's single-list construction
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — all arrays same length as `number_of_deferrable_loads`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_array_lengths"`
  - **Commit**: `test(sensor): green - verify array length consistency`
  - _Requirements: AC-3.5_

- [ ] 1.43 [RED] Failing test: aggregated sensor excludes inactive trips from matrix
  - **Do**:
    1. Write test `test_aggregated_sensor_excludes_inactive` with 2 active + 1 inactive (`activo=False`) trip
    2. Assert matrix has 2 rows (not 3), inactive trip excluded from all arrays
  - **Files**: tests/test_sensor_coverage.py
  - **Done when**: Test exists AND fails (or passes if filter already works)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_excludes_inactive" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS || echo GREEN_PASS`
  - **Commit**: `test(sensor): red - failing test for inactive trip exclusion`

- [ ] 1.44 [GREEN] Verify inactive trip exclusion
  - **Do**: Run test — should pass from 1.40's `activo=True` filter
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — inactive trips excluded
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_excludes_inactive"`
  - **Commit**: `test(sensor): green - verify inactive trips excluded from matrix`
  - _Requirements: FR-7_

- [ ] 1.45 [RED] Failing test: `_get_active_trips_ordered` sorts by emhass_index ascending
  - **Do**:
    1. Write test `test_get_active_trips_ordered_sorting` with trips having indices [3, 1, 2]
    2. Assert sorted result is [1, 2, 3] order
  - **Files**: tests/test_sensor_coverage.py
  - **Done when**: Test exists AND fails (or passes if sort already correct)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_get_active_trips_ordered_sorting" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS || echo GREEN_PASS`
  - **Commit**: `test(sensor): red - failing test for active trips ordering`

- [ ] 1.46 [GREEN] Verify `_get_active_trips_ordered` sorting
  - **Do**: Run test — should pass from 1.40's sort key
  - **Files**: custom_components/ev_trip_planner/sensor.py
  - **Done when**: Test passes — trips sorted by emhass_index ascending
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_get_active_trips_ordered_sorting"`
  - **Commit**: `test(sensor): green - verify active trips ordering by emhass_index`
  - _Requirements: AC-3.3_

- [ ] V4c [VERIFY] Quality checkpoint: aggregated sensor extensions
  - **Do**: Run quality commands
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x && ruff check custom_components/ev_trip_planner/sensor.py && mypy custom_components/ev_trip_planner/sensor.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(sensor): pass quality checkpoint after aggregated sensor extensions`

## Phase 1 (continued): TDD Cycles — TripManager Integration + Legacy Refactor

Focus: Refactor trip_manager to use sensor.py CRUD functions + add EMHASS sensor CRUD calls.

- [ ] 1.47 [RED] Failing test: trip_manager `async_add_recurring_trip` calls sensor.py `async_create_trip_sensor`
  - **Do**:
    1. In `tests/test_trip_manager.py`, write test `test_add_recurring_calls_sensor_py_create` that mocks `sensor.async_create_trip_sensor`
    2. Assert `async_create_trip_sensor(hass, entry_id, trip_data)` called (not `self.async_create_trip_sensor`)
  - **Files**: tests/test_trip_manager.py
  - **Done when**: Test exists AND fails — trip_manager still calls internal method
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_add_recurring_calls_sensor_py_create" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(trip_manager): red - failing test for sensor.py create call refactor`
  - _Design: Component 6_

- [ ] 1.48 [GREEN] Refactor recurring trip sensor CRUD to use sensor.py functions
  - **Do**:
    1. At trip_manager.py:481, replace `await self.async_create_trip_sensor(trip_id, ...)` with `await async_create_trip_sensor(self.hass, self._entry_id, trip_data)`
    2. Add import for `async_create_trip_sensor` from sensor.py
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Test passes — sensor.py function called instead of internal method
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_add_recurring_calls_sensor_py_create"`
  - **Commit**: `refactor(trip_manager): use sensor.py async_create_trip_sensor for recurring trips`
  - _Design: Component 6_

- [ ] 1.49 [GREEN] Refactor punctual trip sensor CRUD at line 524
  - **Do**:
    1. At trip_manager.py:524, replace `await self.async_create_trip_sensor(trip_id, ...)` with `await async_create_trip_sensor(self.hass, self._entry_id, trip_data)`
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Punctual trip creation also uses sensor.py function
  - **Verify**: `grep -n "async_create_trip_sensor" custom_components/ev_trip_planner/trip_manager.py | grep -v "import" | head -5`
  - **Commit**: `refactor(trip_manager): use sensor.py async_create_trip_sensor for punctual trips`

- [ ] 1.50 [GREEN] Refactor trip delete sensor CRUD at line 604
  - **Do**:
    1. At trip_manager.py:604, replace `await self.async_remove_trip_sensor(trip_id)` with `await async_remove_trip_sensor(self.hass, self._entry_id, trip_id)`
    2. Add import for `async_remove_trip_sensor` from sensor.py
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Trip deletion uses sensor.py function
  - **Verify**: `grep -n "async_remove_trip_sensor" custom_components/ev_trip_planner/trip_manager.py | grep -v "import\|async def" | head -5`
  - **Commit**: `refactor(trip_manager): use sensor.py async_remove_trip_sensor for trip deletion`

- [ ] 1.51 [GREEN] Remove dead internal CRUD methods (lines 1891-1993)
  - **Do**:
    1. Delete `TripManager.async_create_trip_sensor` (lines 1890-1952)
    2. Delete `TripManager.async_remove_trip_sensor` (lines 1954-2002)
    3. Verify no other references to these internal methods
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Internal methods removed, no references remain
  - **Verify**: `grep -n "self.async_create_trip_sensor\|self.async_remove_trip_sensor" custom_components/ev_trip_planner/trip_manager.py && echo FAIL || echo PASS`
  - **Commit**: `refactor(trip_manager): remove dead internal sensor CRUD methods`
  - _Design: Component 6_

- [ ] V5a [VERIFY] Quality checkpoint: legacy refactor
  - **Do**: Run quality commands
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -x --ignore=tests/e2e/ --ignore=tests/ha-manual/ && ruff check custom_components/ev_trip_planner/trip_manager.py && mypy custom_components/ev_trip_planner/trip_manager.py --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(trip_manager): pass quality checkpoint after legacy refactor`

- [ ] 1.52 [RED] Failing test: trip_manager `async_add_recurring_trip` calls EMHASS sensor create
  - **Do**:
    1. Write test `test_add_recurring_calls_emhass_sensor_create` asserting `async_create_trip_emhass_sensor` is called after `async_create_trip_sensor`
  - **Files**: tests/test_trip_manager.py
  - **Done when**: Test exists AND fails — EMHASS sensor CRUD not yet added
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_add_recurring_calls_emhass_sensor_create" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(trip_manager): red - failing test for EMHASS sensor create on recurring add`
  - _Requirements: FR-5_

- [ ] 1.53 [GREEN] Add EMHASS sensor CRUD calls for recurring trip creation
  - **Do**:
    1. At trip_manager.py:481, after `async_create_trip_sensor` call, add `await async_create_trip_emhass_sensor(self.hass, self._entry_id, trip_data)`
    2. Import `async_create_trip_emhass_sensor` from sensor.py
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Test passes — EMHASS sensor created alongside TripSensor
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_add_recurring_calls_emhass_sensor_create"`
  - **Commit**: `feat(trip_manager): add EMHASS sensor create for recurring trips`
  - _Requirements: FR-5_

- [ ] 1.54 [RED] Failing test: trip_manager `async_add_punctual_trip` calls EMHASS sensor create
  - **Do**:
    1. Write test `test_add_punctual_calls_emhass_sensor_create` asserting `async_create_trip_emhass_sensor` called
  - **Files**: tests/test_trip_manager.py
  - **Done when**: Test exists AND fails — EMHASS CRUD not yet added for punctual
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_add_punctual_calls_emhass_sensor_create" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(trip_manager): red - failing test for EMHASS sensor create on punctual add`

- [ ] 1.55 [GREEN] Add EMHASS sensor CRUD calls for punctual trip creation
  - **Do**:
    1. At trip_manager.py:524, after `async_create_trip_sensor` call, add `await async_create_trip_emhass_sensor(self.hass, self._entry_id, trip_data)`
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Test passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_add_punctual_calls_emhass_sensor_create"`
  - **Commit**: `feat(trip_manager): add EMHASS sensor create for punctual trips`

- [ ] 1.56 [RED] Failing test: trip_manager delete calls EMHASS sensor removal
  - **Do**:
    1. Write test `test_delete_calls_emhass_sensor_remove` asserting `async_remove_trip_emhass_sensor` called
  - **Files**: tests/test_trip_manager.py
  - **Done when**: Test exists AND fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_delete_calls_emhass_sensor_remove" 2>&1 | grep -qi "fail\|error\|assert" && echo RED_PASS`
  - **Commit**: `test(trip_manager): red - failing test for EMHASS sensor removal on delete`

- [ ] 1.57 [GREEN] Add EMHASS sensor removal call for trip deletion
  - **Do**:
    1. At trip_manager.py:604, after `async_remove_trip_sensor` call, add `await async_remove_trip_emhass_sensor(self.hass, self._entry_id, trip_id)`
    2. Import `async_remove_trip_emhass_sensor` from sensor.py
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Test passes — EMHASS sensor removed on trip delete
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager.py -x -k "test_delete_calls_emhass_sensor_remove"`
  - **Commit**: `feat(trip_manager): add EMHASS sensor removal on trip delete`
  - _Requirements: FR-6_

- [ ] V5b [VERIFY] Quality checkpoint: EMHASS sensor CRUD integration
  - **Do**: Run full test suite + lint + typecheck
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -x --ignore=tests/e2e/ --ignore=tests/ha-manual/ && ruff check custom_components/ev_trip_planner/ && mypy custom_components/ev_trip_planner/ --exclude tests/ha-manual --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(emhass): pass quality checkpoint after EMHASS sensor CRUD integration`

## Phase 1 (continued): TDD Cycles — Frontend & Docs

Focus: Panel Jinja2 config section + EMHASS documentation.

- [ ] 1.58 [P] Add EMHASS config section in panel.js with Jinja2 template + copy button
  - **Do**:
    1. In `custom_components/ev_trip_planner/frontend/panel.js`, add `_renderEmhassConfig()` method after sensors section in `render()`
    2. Method returns Lit html card with: title "EMHASS Configuration", Jinja2 template text for all 6 parameters referencing the aggregated sensor entity
    3. Add copy button using `navigator.clipboard.writeText()`, show visual confirmation
    4. Template references sensor entity from `this._hass.states` matching current vehicle
  - **Files**: custom_components/ev_trip_planner/frontend/panel.js
  - **Done when**: EMHASS config section renders with copyable template
  - **Verify**: `grep -q "_renderEmhassConfig" custom_components/ev_trip_planner/frontend/panel.js && echo PASS`
  - **Commit**: `feat(panel): add EMHASS Jinja2 config section with copy button`
  - _Requirements: FR-10, AC-4.1-4.4_

- [ ] 1.59 [P] Create EMHASS setup documentation
  - **Do**:
    1. Create `docs/emhass-setup.md` with: introduction, prerequisites, sensor reference table, complete Jinja2 templates for all 6 params, EMHASS optimize configuration example, troubleshooting section
  - **Files**: docs/emhass-setup.md
  - **Done when**: Documentation file exists with all sections
  - **Verify**: `test -f docs/emhass-setup.md && grep -q "P_deferrable" docs/emhass-setup.md && echo PASS`
  - **Commit**: `docs(emhass): add EMHASS setup documentation with Jinja2 templates`
  - _Requirements: FR-11, AC-5.1-5.3_

- [ ] V5c [VERIFY] Quality checkpoint: frontend + docs
  - **Do**: Verify panel.js parses and docs exist
  - **Verify**: `node -c custom_components/ev_trip_planner/frontend/panel.js && test -f docs/emhass-setup.md && echo PASS`
  - **Done when**: Panel.js syntax valid, docs file exists
  - **Commit**: `chore(emhass): pass quality checkpoint after frontend + docs`

## Phase 2: Additional Testing

Focus: Integration tests spanning multiple components, edge case coverage.

- [ ] 2.1 Integration test: full data flow from adapter cache to sensor attributes
  - **Do**:
    1. Write test `test_data_flow_adapter_to_sensors` that:
       - Creates adapter with mock trips, calls `publish_deferrable_loads`
       - Creates coordinator with adapter data
       - Creates `TripEmhassSensor` and `EmhassDeferrableLoadSensor` with coordinator
       - Asserts per-trip sensor has correct attributes, aggregated sensor has correct matrix
  - **Files**: tests/test_sensor_coverage.py
  - **Done when**: Test passes — data flows correctly from adapter through coordinator to both sensor types
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_data_flow_adapter_to_sensors"`
  - **Commit**: `test(emhass): add integration test for adapter-to-sensor data flow`

- [ ] 2.2 Integration test: no active trips produces empty matrix
  - **Do**:
    1. Write test `test_aggregated_sensor_empty_when_no_active_trips` with all trips inactive
    2. Assert `p_deferrable_matrix=[]`, `number_of_deferrable_loads=0`, all arrays empty
  - **Files**: tests/test_sensor_coverage.py
  - **Done when**: Test passes — empty state handled correctly
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_sensor_coverage.py -x -k "test_aggregated_sensor_empty_when_no_active"`
  - **Commit**: `test(emhass): add test for empty matrix when no active trips`

- [ ] 2.3 Integration test: charging power update propagates to sensor attributes
  - **Do**:
    1. Write test `test_charging_power_update_propagates` that:
       - Creates adapter with initial power 11kW, publishes trips
       - Updates entry.options to 3.6kW, triggers config entry listener
       - Verifies sensor attributes reflect new power via coordinator refresh
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test passes — power change flows through to sensor attrs
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_charging_power_update_propagates"`
  - **Commit**: `test(emhass): add integration test for charging power update propagation`

- [ ] 2.4 Edge case test: multiple trips with same deadline get separate indices
  - **Do**:
    1. Write test with 3 trips having same deadline datetime
    2. Assert each gets separate `emhass_index`, separate matrix row
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test passes — no index collision
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_multiple_trips_same_deadline"`
  - **Commit**: `test(emhass): add edge case test for multiple trips same deadline`

- [ ] 2.5 Edge case test: trip deadline in past
  - **Do**:
    1. Write test `test_past_deadline_trip` — trip with deadline in past
    2. Assert `async_publish_deferrable_load` returns False, no index assigned
  - **Files**: tests/test_emhass_adapter.py
  - **Done when**: Test passes — past deadline handled correctly
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_emhass_adapter.py -x -k "test_past_deadline_trip"`
  - **Commit**: `test(emhass): add edge case test for past deadline trip`

- [ ] 2.6 [VERIFY] Quality checkpoint: additional tests pass
  - **Do**: Run full test suite + lint + typecheck
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -x --ignore=tests/e2e/ --ignore=tests/ha-manual/ && ruff check . && mypy custom_components/ tests/ --exclude tests/ha-manual --no-namespace-packages`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(emhass): pass quality checkpoint after additional tests`

## Phase 3: Quality Gates

- [ ] V4 [VERIFY] Full local CI: test + lint + typecheck
  - **Do**: Run complete local CI suite
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -x --ignore=tests/e2e/ --ignore=tests/ha-manual/ && ruff check . && pylint custom_components/ tests/ && mypy custom_components/ tests/ --exclude tests/ha-manual --no-namespace-packages`
  - **Done when**: All tests pass, lint clean, typecheck clean
  - **Commit**: `chore(emhass): pass full local CI` (if fixes needed)

- [ ] 3.1 Verify 100% test coverage on changed modules
  - **Do**: Run coverage report and verify all changed modules at 100%
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Done when**: Coverage report shows 100% on emhass_adapter.py, sensor.py, trip_manager.py, __init__.py
  - **Commit**: `chore(emhass): ensure 100% test coverage on changed modules`
  - _Requirements: NFR-1_

- [ ] 3.2 [P] Fix any coverage gaps found in 3.1
  - **Do**: Add tests for any uncovered lines/branches identified by coverage report
  - **Files**: tests/test_emhass_adapter.py, tests/test_sensor_coverage.py, tests/test_trip_manager.py
  - **Done when**: `make test-cover` passes with 100% coverage
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ --cov=custom_components.ev_trip_planner --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Commit**: `test(emhass): fix coverage gaps to reach 100%`
  - _Requirements: NFR-1_

- [ ] V5 [VERIFY] CI pipeline passes
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin <branch-name>`
    3. Create PR using gh CLI
    4. Verify CI passes
  - **Verify**: `gh pr checks`
  - **Done when**: All CI checks green
  - **Commit**: None

- [ ] V6 [VERIFY] AC checklist: programmatically verify all acceptance criteria
  - **Do**:
    1. AC-1.1: `grep -q "entry.options.get" custom_components/ev_trip_planner/emhass_adapter.py`
    2. AC-1.2: `grep -q "setup_config_entry_listener" custom_components/ev_trip_planner/__init__.py`
    3. AC-1.3: `grep -q "not self._published_trips" custom_components/ev_trip_planner/emhass_adapter.py`
    4. AC-2.1-2.6: `grep -q "class TripEmhassSensor" custom_components/ev_trip_planner/sensor.py`
    5. AC-3.1-3.5: `grep -q "p_deferrable_matrix" custom_components/ev_trip_planner/sensor.py`
    6. AC-4.1-4.4: `grep -q "_renderEmhassConfig" custom_components/ev_trip_planner/frontend/panel.js`
    7. AC-5.1-5.3: `test -f docs/emhass-setup.md`
    8. Run all tests: `make test`
  - **Verify**: All grep commands return 0 and all tests pass
  - **Done when**: All acceptance criteria confirmed met via automated checks
  - **Commit**: None

## Phase 4: PR Lifecycle

- [ ] 4.1 Monitor CI and fix any failures
  - **Do**:
    1. Check CI status: `gh pr checks`
    2. If failures, read logs, fix locally, push
    3. Re-verify until all green
  - **Verify**: `gh pr checks`
  - **Done when**: All CI checks green
  - **Commit**: `fix(emhass): address CI failures` (if needed)

- [ ] 4.2 Resolve code review comments
  - **Do**:
    1. Check for review comments: `gh pr view --json reviews`
    2. Address each comment with code fix or reply
    3. Push fixes
  - **Verify**: No unresolved review comments
  - **Done when**: All review comments addressed
  - **Commit**: `fix(emhass): address review comments` (if needed)

- [ ] 4.3 Final validation: zero regressions + modularity
  - **Do**:
    1. Run `make check` — all tests, lint, mypy pass
    2. Verify no regression: all 1376+ existing tests pass
    3. Verify modularity: no class > 200 lines
  - **Verify**: `make check`
  - **Done when**: Full check passes with zero errors
  - **Commit**: `chore(emhass): final validation before merge`

## Notes

- **TDD approach**: All implementation driven by failing tests first (25 RED tasks, 28 GREEN tasks)
- **POC shortcuts taken**: None — TDD workflow, no shortcuts
- **Production TODOs**: None — all features fully implemented
- **Key patterns followed**: `TripSensor` for `TripEmhassSensor`, `async_create_trip_sensor` for `async_create_trip_emhass_sensor`, `_cached_power_profile` for `_cached_per_trip_params`
- **Critical `self.hass` note**: emhass_adapter.py:43 stores as `self.hass` (NOT `self._hass`)
- **`inicio_ventana` is datetime, not int**: Must convert to timestep via `(dt - now).total_seconds() / 3600`
- **`is None` not `or` for options read**: Prevents `charging_power_kw=0` edge case being treated as falsy
- **No `_calculate_individual_power_profile` wrapper**: Uses existing `_calculate_power_profile_from_trips([trip], power)` directly
- **TripEmhassSensor tests in separate file**: `tests/test_trip_emhass_sensor.py` (SRP), aggregated sensor tests stay in `test_sensor_coverage.py`
- **Freezegun for timestep tests**: Task 1.13 uses `@freeze_time` for deterministic `datetime.now()` in timestep conversion
