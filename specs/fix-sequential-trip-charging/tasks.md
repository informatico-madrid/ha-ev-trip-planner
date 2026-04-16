# Tasks: Fix Sequential Trip Charging

## Phase 1: Make It Work (POC)

Focus: Validate the core fix works - batch process trips and get correct def_start_timestep. Skip tests, accept hardcoded values. Only type check must pass.

- [ ] 1.1 Add CONF_RETURN_BUFFER_HOURS and defaults to const.py
  - **Do**:
    1. Add `CONF_RETURN_BUFFER_HOURS = "return_buffer_hours"` constant
    2. Add `DEFAULT_RETURN_BUFFER_HOURS = 4.0`
    3. Add `MIN_RETURN_BUFFER_HOURS = 0.0`
    4. Add `MAX_RETURN_BUFFER_HOURS = 12.0`
  - **Files**: custom_components/ev_trip_planner/const.py
  - **Done when**: Constants exported and importable
  - **Verify**: `PYTHONPATH=. python3 -c "from custom_components.ev_trip_planner.const import CONF_RETURN_BUFFER_HOURS, DEFAULT_RETURN_BUFFER_HOURS; print(CONF_RETURN_BUFFER_HOURS, DEFAULT_RETURN_BUFFER_HOURS)"`
  - **Commit**: `feat(sequential-trip): add return_buffer_hours constants to const.py`
  - _Requirements: FR-4_
  - _Design: Component 3_

- [ ] 1.2 [P] Add return_buffer_hours to STEP_EMHASS_SCHEMA in config_flow.py
  - **Do**:
    1. Import `CONF_RETURN_BUFFER_HOURS, DEFAULT_RETURN_BUFFER_HOURS` from const
    2. Add `vol.Optional(CONF_RETURN_BUFFER_HOURS, default=DEFAULT_RETURN_BUFFER_HOURS)` with `vol.All(vol.Coerce(float), vol.Range(min=0.0, max=12.0))` validator to STEP_EMHASS_SCHEMA
    3. Add Spanish description string for the field
  - **Files**: custom_components/ev_trip_planner/config_flow.py
  - **Done when**: Config schema accepts return_buffer_hours option
  - **Verify**: `PYTHONPATH=. python3 -c "from custom_components.ev_trip_planner.config_flow import STEP_EMHASS_SCHEMA; print(STEP_EMHASS_SCHEMA)"`
  - **Commit**: `feat(sequential-trip): add return_buffer_hours config option`
  - _Requirements: FR-3, AC-2.1, AC-2.2_
  - _Design: Component 4_

- [ ] 1.3 [P] Add return_buffer_hours import to config_flow.py
  - **Do**:
    1. Add `CONF_RETURN_BUFFER_HOURS` and `DEFAULT_RETURN_BUFFER_HOURS` to the import block from `.const`
  - **Files**: custom_components/ev_trip_planner/config_flow.py
  - **Done when**: Import resolves without error
  - **Verify**: `PYTHONPATH=. python3 -c "from custom_components.ev_trip_planner.config_flow import STEP_EMHASS_SCHEMA; print('OK')"`
  - **Commit**: `feat(sequential-trip): import return_buffer_hours constants in config_flow`
  - _Requirements: FR-3, FR-4_
  - _Design: Component 4_

- [ ] 1.4 [VERIFY] Quality checkpoint: type check passes after const.py and config_flow.py changes
  - **Do**: Run mypy on modified files
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/const.py custom_components/ev_trip_planner/config_flow.py --no-namespace-packages`
  - **Done when**: No type errors
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after const/config changes`

- [ ] 1.5 Store return_buffer_hours in EMHASSAdapter.__init__
  - **Do**:
    1. Import `CONF_RETURN_BUFFER_HOURS, DEFAULT_RETURN_BUFFER_HOURS` from const
    2. Read `return_buffer_hours` from entry_data with DEFAULT_RETURN_BUFFER_HOURS fallback
    3. Store as `self._return_buffer_hours`
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: `self._return_buffer_hours` initialized from config or default
  - **Verify**: `PYTHONPATH=. python3 -c "from custom_components.ev_trip_planner.const import CONF_RETURN_BUFFER_HOURS; print(CONF_RETURN_BUFFER_HOURS + ' importable')"`
  - **Commit**: `feat(sequential-trip): store return_buffer_hours in EMHASSAdapter init`
  - _Requirements: FR-3, AC-2.5_
  - _Design: Component 1_

- [ ] 1.6 Rename duration_hours to return_buffer_hours in calculate_multi_trip_charging_windows signature
  - **Do**:
    1. Change parameter name `duration_hours: float = 6.0` to `return_buffer_hours: float = 6.0` in function signature
    2. Update docstring to clarify this is gap between trips (return buffer), not trip duration
    3. Update default value to 6.0 (keep backward compat for now, will change to 4.0 in Phase 2)
  - **Files**: custom_components/ev_trip_planner/calculations.py
  - **Done when**: Function signature uses return_buffer_hours, docstring updated
  - **Verify**: `PYTHONPATH=. python3 -c "import inspect; from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows; sig = inspect.signature(calculate_multi_trip_charging_windows); print([p for p in sig.parameters if 'buffer' in p or 'duration' in p])"`
  - **Commit**: `refactor(sequential-trip): rename duration_hours to return_buffer_hours parameter`
  - _Requirements: FR-2_
  - _Design: Component 2_

- [ ] 1.7 Update internal references to duration_hours in calculate_multi_trip_charging_windows body
  - **Do**:
    1. Replace all internal uses of `duration_hours` with `return_buffer_hours` inside the function body (lines ~376-382)
    2. Verify the logic for `window_start` fallback and `trip_arrival` calculation still uses `return_buffer_hours`
  - **Files**: custom_components/ev_trip_planner/calculations.py
  - **Done when**: No references to `duration_hours` remain in the function body
  - **Verify**: `grep -n "duration_hours" custom_components/ev_trip_planner/calculations.py | grep -v "# " || echo "NO_DURATION_HOURS_REFS"`
  - **Commit**: `refactor(sequential-trip): update internal refs to return_buffer_hours`
  - _Requirements: FR-2_
  - _Design: Component 2_

- [ ] 1.8 [VERIFY] Quality checkpoint: type check + lint after calculations.py rename
  - **Do**: Run mypy and ruff on calculations.py
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/calculations.py --no-namespace-packages && ruff check custom_components/ev_trip_planner/calculations.py`
  - **Done when**: No type errors, no lint errors
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after calculations rename`

- [ ] 1.9 Update caller in async_publish_deferrable_load to use return_buffer_hours keyword
  - **Do**:
    1. In `async_publish_deferrable_load` (~line 363-368), change `duration_hours=6.0` to `return_buffer_hours=self._return_buffer_hours`
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Caller uses `return_buffer_hours` keyword with config value
  - **Verify**: `grep -n "return_buffer_hours=self._return_buffer_hours" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `fix(sequential-trip): use return_buffer_hours config in async_publish_deferrable_load`
  - _Requirements: FR-2, FR-3_
  - _Design: Component 1_

- [ ] 1.10 Update caller in _populate_per_trip_cache_entry to use return_buffer_hours keyword
  - **Do**:
    1. In `_populate_per_trip_cache_entry` (~line 531-537), change `duration_hours=6.0` to `return_buffer_hours=self._return_buffer_hours`
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Caller uses `return_buffer_hours` keyword with config value
  - **Verify**: `grep -n "return_buffer_hours=self._return_buffer_hours" custom_components/ev_trip_planner/emhass_adapter.py | wc -l | grep -q "2" && echo PASS`
  - **Commit**: `fix(sequential-trip): use return_buffer_hours config in _populate_per_trip_cache_entry`
  - _Requirements: FR-2, FR-3_
  - _Design: Component 1_

- [ ] 1.11 Add batch charging windows computation before per-trip loop in async_publish_all_deferrable_loads
  - **Do**:
    1. Before the `for trip in trips:` loop at ~line 633, collect all trip deadlines
    2. Call `calculate_multi_trip_charging_windows()` ONCE with ALL trips
    3. Store result in local variable `batch_charging_windows`
    4. Log the batch computation for debug visibility
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: `calculate_multi_trip_charging_windows` called with all trips before per-trip loop
  - **Verify**: `grep -n "batch_charging_windows" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `feat(sequential-trip): batch compute charging windows before per-trip loop`
  - _Requirements: FR-1_
  - _Design: Component 1, Data Flow step 2_

- [ ] 1.12 Map batch_charging_windows to per-trip def_start_timestep in async_publish_all_deferrable_loads
  - **Do**:
    1. After batch computation, create mapping dict `window_by_trip_id = {}`
    2. For each trip, extract `window["inicio_ventana"]` and convert to timestep offset
    3. Store timestep in `window_by_trip_id[trip_id]`
    4. Pass pre-computed timestep to `_populate_per_trip_cache_entry`
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Each trip gets its def_start_timestep from batch computation
  - **Verify**: `grep -n "window_by_trip_id\|batch_window" custom_components/ev_trip_planner/emhass_adapter.py | head -5`
  - **Commit**: `feat(sequential-trip): map batch windows to per-trip def_start_timestep`
  - _Requirements: FR-1, FR-2_
  - _Design: Component 1, Data Flow step 3_

- [ ] 1.13 [VERIFY] Quality checkpoint: type check after emhass_adapter batch processing changes
  - **Do**: Run mypy on emhass_adapter.py
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/emhass_adapter.py --no-namespace-packages`
  - **Done when**: No type errors
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after batch processing`

- [ ] 1.14 Modify _populate_per_trip_cache_entry to accept optional pre-computed def_start_timestep
  - **Do**:
    1. Add `pre_computed_def_start_timestep: Optional[int] = None` parameter to method signature
    2. If pre_computed value is not None, use it instead of calling `calculate_multi_trip_charging_windows` locally
    3. If pre_computed value is None, fall back to existing single-trip calculation (backward compat)
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Method accepts and uses pre-computed timestep when provided
  - **Verify**: `grep -n "pre_computed_def_start_timestep" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `feat(sequential-trip): accept pre-computed def_start_timestep in cache entry`
  - _Requirements: FR-1, FR-5_
  - _Design: Component 1_

- [ ] 1.15 Pass batch-computed timestep from async_publish_all_deferrable_loads to _populate_per_trip_cache_entry
  - **Do**:
    1. In the per-trip loop at ~line 671-677, pass `window_by_trip_id.get(trip_id)` as `pre_computed_def_start_timestep`
    2. Remove or skip the local charging_windows call when pre-computed value is available
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Per-trip loop uses batch-computed timestep
  - **Verify**: `grep -n "pre_computed_def_start_timestep" custom_components/ev_trip_planner/emhass_adapter.py | grep "await self._populate" | head -1`
  - **Commit**: `feat(sequential-trip): pass batch timestep to per-trip cache entry`
  - _Requirements: FR-1, FR-2_
  - _Design: Component 1, Data Flow step 4_

- [ ] 1.16 Add edge case: cap def_start_timestep at def_end_timestep when buffer exceeds gap
  - **Do**:
    1. After computing def_start_timestep, compare with def_end_timestep
    2. If def_start_timestep >= def_end_timestep, cap at def_end_timestep - 1 (minimum 1 hour window)
    3. Log warning when capping occurs
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: def_start_timestep never exceeds def_end_timestep
  - **Verify**: `grep -n "cap\|capped\|window_start > deadline\|def_start_timestep >= def_end_timestep" custom_components/ev_trip_planner/emhass_adapter.py | head -3`
  - **Commit**: `fix(sequential-trip): cap def_start_timestep at deadline when buffer exceeds gap`
  - _Requirements: FR-2_
  - _Design: Error Handling table_

- [ ] 1.17 [VERIFY] Quality checkpoint: type check + lint after emhass_adapter edge case handling
  - **Do**: Run mypy and ruff on emhass_adapter.py
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/emhass_adapter.py --no-namespace-packages && ruff check custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: No type errors, no lint errors
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after edge case handling`

- [ ] 1.18 Add reactive update: reload return_buffer_hours from config entry options
  - **Do**:
    1. In `update_charging_power` method (~line 1695), also read `return_buffer_hours` from entry.options
    2. If return_buffer_hours changed, update `self._return_buffer_hours` and trigger republish
    3. Log the change for debugging
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Config change triggers republish with new buffer value
  - **Verify**: `grep -n "return_buffer_hours" custom_components/ev_trip_planner/emhass_adapter.py | head -8`
  - **Commit**: `feat(sequential-trip): reactive update return_buffer_hours from config`
  - _Requirements: FR-7, AC-2.4_
  - _Design: Component 1_

- [ ] 1.19 Add _get_return_buffer_hours helper method
  - **Do**:
    1. Create `_get_return_buffer_hours(self) -> float` method that reads from config entry options first, then data, then default
    2. Use same pattern as `update_charging_power`: entry.options -> entry.data -> DEFAULT_RETURN_BUFFER_HOURS
    3. Use this in `__init__` and `update_charging_power` instead of inline reads
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Helper method exists and is used by init and reactive update
  - **Verify**: `grep -n "_get_return_buffer_hours" custom_components/ev_trip_planner/emhass_adapter.py | head -4`
  - **Commit**: `refactor(sequential-trip): extract _get_return_buffer_hours helper`
  - _Requirements: FR-3, FR-7_
  - _Design: Component 1_

- [ ] 1.20 [VERIFY] Quality checkpoint: full type check + lint after all Phase 1 changes
  - **Do**: Run mypy and ruff on all modified files
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/`
  - **Done when**: No type errors, no lint errors across all modified files
  - **Commit**: `chore(sequential-trip): pass quality checkpoint end of Phase 1`

- [ ] 1.21 Run existing tests to verify no regressions
  - **Do**: Run full pytest suite excluding e2e and ha-manual
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ -x`
  - **Done when**: All 1519 tests pass
  - **Commit**: None (verification only)

- [ ] 1.22 POC Checkpoint: verify sequential trip def_start_timestep logic works
  - **Do**:
    1. Write a quick Python script that imports `calculate_multi_trip_charging_windows`
    2. Create 2 trips with sequential deadlines
    3. Call with `return_buffer_hours=4.0`
    4. Verify `results[1]["inicio_ventana"]` is after `results[0]["fin_ventana"]`
    5. Run existing tests again to confirm no regression
  - **Done when**: Script shows trip 2 window starts after trip 1 end + buffer
  - **Verify**: `PYTHONPATH=. python3 -c "
from datetime import datetime, timedelta, timezone
from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows
now = datetime.now(timezone.utc)
trip0_dl = now + timedelta(hours=12)
trip1_dl = now + timedelta(hours=48)
trip0 = {'kwh': 10.0}
trip1 = {'kwh': 20.0}
hora_regreso = now + timedelta(hours=2)
results = calculate_multi_trip_charging_windows(
    trips=[(trip0_dl, trip0), (trip1_dl, trip1)],
    soc_actual=50.0,
    hora_regreso=hora_regreso,
    charging_power_kw=11.0,
    return_buffer_hours=4.0,
)
assert len(results) == 2, f'Expected 2 results, got {len(results)}'
assert results[0]['inicio_ventana'] == hora_regreso, 'Trip 0 should start at hora_regreso'
assert results[1]['inicio_ventana'] > results[0]['fin_ventana'], 'Trip 1 should start after trip 0 ends'
print('POC PASS: sequential charging windows computed correctly')
print(f'  Trip 0: inicio={results[0][\"inicio_ventana\"]}, fin={results[0][\"fin_ventana\"]}')
print(f'  Trip 1: inicio={results[1][\"inicio_ventana\"]}, fin={results[1][\"fin_ventana\"]}')
"
  - **Commit**: `feat(sequential-trip): complete POC - sequential charging windows validated`

## Phase 2: Refactoring

After POC validated, clean up code. Type check must pass.

- [ ] 2.1 Update calculate_multi_trip_charging_windows default to 4.0
  - **Do**:
    1. Change `return_buffer_hours: float = 6.0` to `return_buffer_hours: float = 4.0` in function signature
    2. Update docstring to reflect new default (4.0h)
  - **Files**: custom_components/ev_trip_planner/calculations.py
  - **Done when**: Default is 4.0h matching DEFAULT_RETURN_BUFFER_HOURS
  - **Verify**: `grep "return_buffer_hours.*4.0" custom_components/ev_trip_planner/calculations.py`
  - **Commit**: `refactor(sequential-trip): update return_buffer_hours default to 4.0`
  - _Design: Component 2_

- [ ] 2.2 [P] Add Spanish comments to batch processing logic in emhass_adapter.py
  - **Do**:
    1. Add Spanish comments explaining batch processing: "Calcula ventanas de carga para todos los viajes de forma secuencial"
    2. Add comments to edge case capping logic
    3. Follow existing Spanish comment pattern in codebase
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: New code has Spanish comments matching codebase style
  - **Verify**: `grep -c "# " custom_components/ev_trip_planner/emhass_adapter.py | awk '{print "Comment lines: "$1}'`
  - **Commit**: `refactor(sequential-trip): add Spanish comments to batch processing`

- [ ] 2.3 [P] Add debug logging for sequential offset computation
  - **Do**:
    1. Add `_LOGGER.debug("DEBUG:")` log for batch charging windows result
    2. Log each trip's def_start_timestep from batch computation
    3. Log when edge case capping occurs (warning level)
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Debug logging covers batch computation and edge cases
  - **Verify**: `grep -c "_LOGGER.debug\|_LOGGER.warning" custom_components/ev_trip_planner/emhass_adapter.py | awk '{print $1}'`
  - **Commit**: `refactor(sequential-trip): add debug logging for sequential offsets`
  - _Design: Existing Patterns item 3_

- [ ] 2.4 [VERIFY] Quality checkpoint: type check + lint + tests after refactoring
  - **Do**: Run mypy, ruff, and tests on all modified files
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ -x`
  - **Done when**: No type errors, no lint errors, all tests pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after Phase 2 refactoring`

- [ ] 2.5 Clean up any remaining hardcoded 6.0 references in calculations.py callers
  - **Do**:
    1. Search for any remaining `duration_hours=6.0` or `6.0` references in emhass_adapter.py
    2. Replace with `self._return_buffer_hours` or proper config reference
    3. Verify all callers use the config value
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: No hardcoded buffer duration remains
  - **Verify**: `grep -rn "duration_hours" custom_components/ev_trip_planner/ || echo "NO_DURATION_HOURS_REFS"`
  - **Commit**: `refactor(sequential-trip): remove all hardcoded duration_hours references`

- [ ] 2.6 Verify _published_trips stores trips for reactive republish (FR-6)
  - **Do**:
    1. Confirm `self._published_trips = list(trips)` is called after batch processing in `async_publish_all_deferrable_loads`
    2. Ensure reactive update path uses `_published_trips` to republish with new buffer
    3. Verify the reactive update call chain works: config change -> update_charging_power -> publish_deferrable_loads -> async_publish_all_deferrable_loads
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Reactive republish uses stored trips with updated buffer
  - **Verify**: `grep -n "_published_trips" custom_components/ev_trip_planner/emhass_adapter.py | head -5`
  - **Commit**: `fix(sequential-trip): ensure published trips stored for reactive updates`
  - _Requirements: FR-6, FR-7_

- [ ] 2.7 [VERIFY] Quality checkpoint: type check + lint + tests after cleanup
  - **Do**: Run mypy, ruff, and tests
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ -x`
  - **Done when**: No type errors, no lint errors, all tests pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after Phase 2 cleanup`

## Phase 3: Testing

Add comprehensive test coverage. All tests must pass.

- [ ] 3.1 Create test factory function for sequential trip test data
  - **Do**:
    1. Add `build_sequential_trips()` fixture/factory in `tests/test_charging_window.py`
    2. Factory returns list of 2-3 trips with sequential deadlines, SOC=50%, hora_regreso
    3. Each trip has known kwh, deadline, so expected offsets are deterministic
  - **Files**: tests/test_charging_window.py
  - **Done when**: Factory function exists and returns valid test trip data
  - **Verify**: `grep -n "build_sequential_trips\|sequential_trip" tests/test_charging_window.py | head -3`
  - **Commit**: `test(sequential-trip): add sequential trip test factory`
  - _Design: Test Strategy, Fixtures & Test Data_

- [ ] 3.2 Write test: two sequential trips with 4h buffer produce correct offsets
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with 2 trips and `return_buffer_hours=4.0`
    2. Assert `results[0]["inicio_ventana"]` == hora_regreso
    3. Assert `results[1]["inicio_ventana"]` > `results[0]["fin_ventana"]`
    4. Assert `len(results) == 2`
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "sequential_offset" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify 2-trip sequential offset calculation`
  - _Requirements: FR-2, AC-1.1_
  - _Design: Test Coverage Table row 1_

- [ ] 3.3 Write test: single trip backward compatibility (def_start_timestep = 0)
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with 1 trip
    2. Assert `len(results) == 1`
    3. Assert `results[0]["inicio_ventana"]` == hora_regreso
    4. Assert def_start_timestep remains 0 for single trip scenario
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "single_trip_backward" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify single trip backward compatibility`
  - _Requirements: FR-5, AC-1.3_
  - _Design: Test Coverage Table row 2_

- [ ] 3.4 [VERIFY] Quality checkpoint: type check + new tests pass
  - **Do**: Run mypy and the new tests
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v --tb=short`
  - **Done when**: No type errors, all charging window tests pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after basic tests`

- [ ] 3.5 Write test: three sequential trips with cumulative offsets
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with 3 trips
    2. Assert `inicio_ventana[i]` follows sequential chaining: `inicio_ventana[i] = previous_arrival`
    3. Assert cumulative offset: trip 2 starts after trip 1 arrival
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "three_sequential" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify 3-trip cumulative offset`
  - _Requirements: FR-2, AC-1.2_
  - _Design: Test Coverage Table row 3_

- [ ] 3.6 Write test: window_start capped at deadline when buffer exceeds gap
  - **Do**:
    1. Create 2 trips with tight gap (trip 2 deadline close to trip 1 end + buffer)
    2. Set large return_buffer_hours that would push window_start past deadline
    3. Assert result still returns valid window (not crash)
    4. Assert inicio_ventana does not exceed fin_ventana
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "window_capped\|capped_at_deadline" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify window capped at deadline edge case`
  - _Requirements: FR-2_
  - _Design: Test Coverage Table row 4_

- [ ] 3.7 [VERIFY] Quality checkpoint: all charging window tests pass
  - **Do**: Run full test file
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v --tb=short`
  - **Done when**: All tests in file pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after edge case tests`

- [ ] 3.8 Write test: empty trips list returns empty result
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with `trips=[]`
    2. Assert returns empty list
    3. Assert no crash or exception
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "empty_trips" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify empty trips edge case`
  - _Design: Error Handling table_

- [ ] 3.9 Write test: hora_regreso=None falls back to departure minus buffer
  - **Do**:
    1. Test with `hora_regreso=None` and 1 trip
    2. Assert window_start = trip_departure - return_buffer_hours
    3. Verify fallback calculation is correct
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "hora_regreso_none\|fallback_window" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify hora_regreso None fallback`
  - _Design: Error Handling table_

- [ ] 3.10 Write test: def_end_timestep unchanged after fix (AC-1.4)
  - **Do**:
    1. Compare def_end_timestep values before and after batch processing
    2. Assert def_end_timestep values are identical to single-trip computation
    3. Ensure the fix only affects def_start_timestep
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "end_timestep_unchanged" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify def_end_timestep unchanged`
  - _Requirements: AC-1.4_
  - _Design: Test Coverage Table_

- [ ] 3.11 [VERIFY] Quality checkpoint: all unit tests pass
  - **Do**: Run full test suite on charging_window tests
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v --tb=short`
  - **Done when**: All charging window tests pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after all unit tests`

- [ ] 3.12 Write EMHASSAdapter batch processing integration test (mock HA)
  - **Do**:
    1. Create mock EMHASSAdapter with 2 trips
    2. Stub `_get_current_soc` to return 50.0
    3. Stub `_get_hora_regreso` to return known datetime
    4. Call `async_publish_all_deferrable_loads` with 2 trips
    5. Assert `_cached_per_trip_params[trip0_id]["def_start_timestep"] == 0`
    6. Assert `_cached_per_trip_params[trip1_id]["def_start_timestep"] > 0`
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "batch_processing\|publish_all_sequential" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): add EMHASSAdapter batch processing integration test`
  - _Requirements: FR-1, AC-1.1_
  - _Design: Test Coverage Table row 5_

- [ ] 3.13 Write test: config_flow validates return_buffer_hours range
  - **Do**:
    1. Test STEP_EMHASS_SCHEMA accepts valid value (4.0)
    2. Test STEP_EMHASS_SCHEMA rejects value < 0.0
    3. Test STEP_EMHASS_SCHEMA rejects value > 12.0
    4. Assert voluptuous raises vol.Invalid for out-of-range
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "return_buffer_hours_validation\|buffer_range" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify config validation for return_buffer_hours`
  - _Requirements: FR-3, AC-2.2, NFR-5_
  - _Design: Test Coverage Table row 8-9_

- [ ] 3.14 Write test: two trips with 0 buffer start consecutively
  - **Do**:
    1. Test `return_buffer_hours=0.0`
    2. Assert trip 2 starts exactly at trip 1 arrival (no gap)
    3. Verify consecutive windows with no buffer
  - **Files**: tests/test_charging_window.py
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "zero_buffer\|buffer_zero" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify 0 buffer consecutive trips`
  - _Design: Edge Cases_

- [ ] 3.15 [VERIFY] Quality checkpoint: all tests pass + lint + type check
  - **Do**: Run full test suite, lint, and type check
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after Phase 3 testing`

## Phase 4: Quality Gates

All local checks must pass. Create PR and verify CI.

- [ ] 4.1 Run full test suite to verify zero regressions
  - **Do**: Run complete pytest suite
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Done when**: All 1519+ tests pass with zero failures
  - **Commit**: None (verification only)

- [ ] 4.2 Run lint (ruff + pylint) on all modified files
  - **Do**: Run ruff check and pylint on modified files
  - **Verify**: `ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/pylint custom_components/ev_trip_planner/const.py custom_components/ev_trip_planner/config_flow.py custom_components/ev_trip_planner/emhass_adapter.py custom_components/ev_trip_planner/calculations.py`
  - **Done when**: No lint errors
  - **Commit**: `fix(sequential-trip): address lint issues` (if fixes needed)

- [ ] 4.3 Run mypy type checking on all modified files
  - **Do**: Run mypy on the package
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages`
  - **Done when**: No type errors
  - **Commit**: `fix(sequential-trip): address type errors` (if fixes needed)

- [ ] 4.4 Run make check (full CI: test + lint + mypy)
  - **Do**: Run the project's check target
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && PYTHONPATH=. make check`
  - **Done when**: test + lint + mypy all pass
  - **Commit**: `chore(sequential-trip): pass full local CI` (if fixes needed)

- [ ] V4 [VERIFY] Full local CI: lint && typecheck && test
  - **Do**: Run complete local CI suite (lint, mypy, tests)
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Done when**: All checks pass with zero errors
  - **Commit**: `chore(sequential-trip): pass full local CI`

- [ ] V5 [VERIFY] PR opened correctly
  - **Do**:
    1. Verify current branch: `git branch --show-current`
    2. Push branch: `git push -u origin feat/fix-sequential-trip-charging`
    3. Create PR: `gh pr create --title "fix(sequential-trip): correct def_start_timestep for sequential trips" --body "$(cat <<'EOF'
## Summary
- Fix def_start_timestep_array showing [0, 0] for sequential trips
- Batch process all trips through calculate_multi_trip_charging_windows()
- Add configurable return_buffer_hours option (default 4.0h, range 0-12h)
- Cap def_start_timestep at deadline when buffer exceeds gap between trips

## Test plan
- Unit tests for 2-trip sequential offset calculation
- Unit tests for single trip backward compatibility
- Unit tests for 3-trip cumulative offsets
- Unit tests for edge case (window capped at deadline)
- Unit tests for config validation
- All 1519+ existing tests pass (zero regressions)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"`
    4. Verify PR exists: `gh pr view --json url,state`
  - **Verify**: `gh pr view --json url,state | jq -r '.state'`
  - **Done when**: PR exists on GitHub with state OPEN
  - **Commit**: None

- [ ] V6 [VERIFY] AC checklist
  - **Do**: Programmatically verify each acceptance criteria:
    1. AC-1.1: `grep -r "batch_charging_windows\|window_by_trip_id" custom_components/ev_trip_planner/emhass_adapter.py` && run sequential offset test
    2. AC-1.2: Run 3-trip test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "three_sequential"`
    3. AC-1.3: Run single trip test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "single_trip_backward"`
    4. AC-1.4: Run end_timestep test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "end_timestep_unchanged"`
    5. AC-1.5: Verify p_deferrable_matrix unchanged in code (no modifications to matrix generation)
    6. AC-2.1: `grep "CONF_RETURN_BUFFER_HOURS" custom_components/ev_trip_planner/const.py`
    7. AC-2.2: `grep "vol.Range.*0.0.*12.0" custom_components/ev_trip_planner/config_flow.py`
    8. AC-2.3: `grep "STEP_EMHASS_SCHEMA" custom_components/ev_trip_planner/config_flow.py`
    9. AC-2.4: Run reactive update test or grep for config change handler
    10. AC-2.5: `grep "DEFAULT_RETURN_BUFFER_HOURS.*4.0" custom_components/ev_trip_planner/const.py`
  - **Verify**: All grep commands return matches AND all test commands exit 0
  - **Done when**: All 10 acceptance criteria confirmed met via automated checks
  - **Commit**: None

## Phase 5: PR Lifecycle

Autonomous PR management until all criteria met.

- [ ] 5.1 Monitor CI status and fix failures
  - **Do**:
    1. Check PR CI status: `gh pr checks`
    2. If any check fails, read failure details: `gh pr checks`
    3. Fix issues locally, commit, push
    4. Re-verify CI
  - **Verify**: `gh pr checks 2>&1 | grep -q "passing\|success\|all checks" && echo CI_PASS || echo CI_PENDING`
  - **Done when**: All CI checks green (or no CI configured)
  - **Commit**: `fix(sequential-trip): resolve CI failures` (if needed)

- [ ] 5.2 Address code review comments if any
  - **Do**:
    1. Check for review comments: `gh pr view --comments --json comments`
    2. Address each comment with code fix or reply
    3. Push fixes and verify CI
  - **Verify**: `gh pr view --json reviews | jq '.reviews[].state' | grep -q "APPROVED\|COMMENTED" || echo NO_REVIEWS`
  - **Done when**: All review comments addressed
  - **Commit**: `fix(sequential-trip): address review feedback` (if needed)

- [ ] 5.3 Final validation: zero regressions, modularity, coverage
  - **Do**:
    1. Run full test suite: `PYTHONPATH=. .venv/bin/python -m pytest tests/ --ignore=tests/ha-manual/ --ignore=tests/e2e/`
    2. Verify code is modular: no duplicate charging window logic
    3. Verify coverage: all new code paths tested
    4. Update .progress.md with completion status
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ --ignore=tests/ha-manual/ --ignore=tests/e2e/ -q 2>&1 | tail -3`
  - **Done when**: All tests pass, no regressions, code is modular
  - **Commit**: None

## Unresolved Questions

- **Minimum practical buffer**: Is 0.5h practical for real-world use? (Requirements say 0-12h)
- **Existing trip retroactivity**: Should trips published before this fix be recalculated with new buffer? (Decision: incremental update on next publish)
- **Overlap warning threshold**: When buffer causes window_start > deadline, should we warn only once per trip or every publish? (Decision: warn once per publish)

## Notes

- **POC shortcuts**: Default buffer 6.0 kept initially for backward compat, changed to 4.0 in Phase 2
- **Production TODOs**: Consider StepValue(0.5) validator for 0.5h increments if HA supports it
- **No sensor.py changes needed**: Aggregation already correct, bug is in cache population
- **Key invariant**: p_deferrable_matrix and def_end_timestep_array must remain unchanged
