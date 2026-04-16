# Tasks: Fix Sequential Trip Charging

## Phase 0: Test That Fails First (TDD)

Write a test that demonstrates the bug BEFORE any fix is applied. This test must FAIL with current code and PASS after the fix.

- [x] 0.1 Write failing test: two sequential trips produce def_start_timestep_array with non-zero second element
  - **Do**:
    1. In `tests/test_charging_window.py`, add test `test_sequential_trips_def_start_timestep_offset`
    2. Create 2 trips with sequential deadlines (trip0: +12h, trip1: +48h)
    3. Call `_populate_per_trip_cache_entry()` for each trip (simulating current per-trip behavior)
    4. Assert `def_start_timestep_array[0] == 0` (first trip starts at hora_regreso)
    5. Assert `def_start_timestep_array[1] > 0` (second trip starts AFTER first trip)
    6. This test MUST FAIL with current code (both will be 0)
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and FAILS (demonstrates the bug)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "sequential_trips_def_start" 2>&1 | tail -10`
  - **Commit**: `test(sequential-trip): add failing test for sequential def_start_timestep bug`
  - _Requirements: AC-1.1_
  - _Design: Test Strategy_

- [x] 0.2 [VERIFY] Confirm failing test detects the bug
  - **Do**: Run the new test and confirm it fails with message showing `def_start_timestep_array[1] == 0` (bug)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "sequential_trips_def_start" 2>&1 | grep -i "fail\|assert\|0.*0"`
  - **Done when**: Test fails with clear assertion error showing the bug

## Phase 1: Core Fix

Implement the minimum changes to make the failing test pass.

- [x] 1.1 Add RETURN_BUFFER_HOURS constant to const.py
  - **Do**:
    1. Add `RETURN_BUFFER_HOURS = 4.0` constant after existing defaults section
    2. Add comment: `# Fixed buffer between sequential trip charging windows (hours)`
  - **Files**: `custom_components/ev_trip_planner/const.py`
  - **Done when**: Constant exported and importable
  - **Verify**: `PYTHONPATH=. python3 -c "from custom_components.ev_trip_planner.const import RETURN_BUFFER_HOURS; print(RETURN_BUFFER_HOURS)"`
  - **Commit**: `feat(sequential-trip): add RETURN_BUFFER_HOURS constant`
  - _Requirements: FR-3_
  - _Design: Component 3_

- [x] 1.2 Add return_buffer_hours parameter to calculate_multi_trip_charging_windows()
  - **Do**:
    1. Add `return_buffer_hours: float = 4.0` parameter AFTER `duration_hours` in function signature
    2. Keep `duration_hours: float = 6.0` UNCHANGED (it represents trip duration)
    3. Update docstring to clarify: `duration_hours` = trip duration, `return_buffer_hours` = gap between trips
    4. Import `RETURN_BUFFER_HOURS` is NOT needed here — caller passes it
  - **Files**: `custom_components/ev_trip_planner/calculations.py`
  - **Done when**: Function accepts new parameter without breaking existing callers (default = 4.0)
  - **Verify**: `PYTHONPATH=. python3 -c "import inspect; from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows; sig = inspect.signature(calculate_multi_trip_charging_windows); print([p for p in sig.parameters])"`
  - **Commit**: `feat(sequential-trip): add return_buffer_hours parameter to calculate_multi_trip_charging_windows`
  - _Requirements: FR-4_
  - _Design: Component 2_

- [ ] 1.3 Modify previous_arrival calculation to include return_buffer_hours
  - **Do**:
    1. In `calculate_multi_trip_charging_windows()`, change line 419:
       `previous_arrival = trip_arrival` → `previous_arrival = trip_arrival + timedelta(hours=return_buffer_hours)`
    2. This adds the configurable gap between when a trip ends and the next trip's charging starts
    3. For idx > 0, `window_start = previous_arrival` now includes the buffer
  - **Files**: `custom_components/ev_trip_planner/calculations.py`
  - **Done when**: Sequential trips have buffer gap between them
  - **Verify**: `PYTHONPATH=. python3 -c "
from datetime import datetime, timedelta, timezone
from custom_components.ev_trip_planner.calculations import calculate_multi_trip_charging_windows
now = datetime.now(timezone.utc)
trip0_dl = now + timedelta(hours=12)
trip1_dl = now + timedelta(hours=48)
results = calculate_multi_trip_charging_windows(
    trips=[(trip0_dl, {'kwh': 10.0}), (trip1_dl, {'kwh': 20.0})],
    soc_actual=50.0,
    hora_regreso=now + timedelta(hours=2),
    charging_power_kw=11.0,
    return_buffer_hours=4.0,
)
assert results[1]['inicio_ventana'] > results[0]['fin_ventana'], 'Trip 1 should start after trip 0 end + buffer'
print('PASS: buffer applied correctly')
print(f'  Trip 0 fin_ventana={results[0][\"fin_ventana\"]}')
print(f'  Trip 1 inicio_ventana={results[1][\"inicio_ventana\"]}')
"`
  - **Commit**: `fix(sequential-trip): add return buffer to previous_arrival calculation`
  - _Requirements: FR-2, FR-4_
  - _Design: Component 2_

- [ ] 1.4 [VERIFY] Quality checkpoint: type check + existing tests pass after calculations.py changes
  - **Do**: Run mypy and existing calculation tests
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/calculations.py --no-namespace-packages && PYTHONPATH=. .venv/bin/python -m pytest tests/test_calculations.py -v --tb=short`
  - **Done when**: No type errors, all existing calculation tests pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after calculations changes`

- [ ] 1.5 Add batch charging windows computation in async_publish_all_deferrable_loads()
  - **Do**:
    1. Import `RETURN_BUFFER_HOURS` from const
    2. BEFORE the per-trip cache loop (before line 671), collect all trip deadlines:
       ```python
       trip_deadlines = []
       for trip in trips:
           trip_id = trip.get("id")
           if not trip_id:
               continue
           deadline_dt = self._calculate_deadline_from_trip(trip)
           if deadline_dt:
               trip_deadlines.append((trip_id, deadline_dt, trip))
       ```
    3. Call `calculate_multi_trip_charging_windows()` ONCE with all trips:
       ```python
       batch_charging_windows = {}
       if trip_deadlines:
           windows = calculate_multi_trip_charging_windows(
               trips=[(dl, trip) for _, dl, trip in trip_deadlines],
               soc_actual=soc_current,
               hora_regreso=hora_regreso,
               charging_power_kw=charging_power_kw,
               return_buffer_hours=RETURN_BUFFER_HOURS,
           )
           for i, (trip_id, _, _) in enumerate(trip_deadlines):
               if i < len(windows):
                   batch_charging_windows[trip_id] = windows[i]
       ```
    4. Log batch computation for debug visibility
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: `calculate_multi_trip_charging_windows` called with all trips before per-trip loop
  - **Verify**: `grep -n "batch_charging_windows\|RETURN_BUFFER_HOURS" custom_components/ev_trip_planner/emhass_adapter.py | head -8`
  - **Commit**: `feat(sequential-trip): batch compute charging windows before per-trip loop`
  - _Requirements: FR-1_
  - _Design: Component 1, Data Flow step 2_

- [ ] 1.6 Modify _populate_per_trip_cache_entry() to accept pre-computed inicio_ventana
  - **Do**:
    1. Add `pre_computed_inicio_ventana: Optional[datetime] = None` parameter to method signature
    2. If `pre_computed_inicio_ventana` is not None, use it directly for def_start_timestep calculation:
       ```python
       if pre_computed_inicio_ventana is not None:
           delta_hours = (_ensure_aware(pre_computed_inicio_ventana) - datetime.now(timezone.utc)).total_seconds() / 3600
           def_start_timestep = max(0, min(int(delta_hours), 168))
       ```
    3. If None, fall back to existing single-trip calculation (backward compat)
    4. Add edge case: if `def_start_timestep >= def_end_timestep`, cap at `def_end_timestep - 1` (minimum 0)
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Method accepts and uses pre-computed inicio_ventana when provided
  - **Verify**: `grep -n "pre_computed_inicio_ventana" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `feat(sequential-trip): accept pre-computed inicio_ventana in cache entry`
  - _Requirements: FR-5, FR-6_
  - _Design: Component 4_

- [ ] 1.7 Pass batch-computed inicio_ventana from loop to _populate_per_trip_cache_entry()
  - **Do**:
    1. In the per-trip cache loop (line 671-677), extract batch window for current trip:
       ```python
       batch_window = batch_charging_windows.get(trip_id)
       pre_computed = batch_window.get("inicio_ventana") if batch_window else None
       ```
    2. Pass `pre_computed` to `_populate_per_trip_cache_entry()`:
       ```python
       await self._populate_per_trip_cache_entry(
           trip, trip_id, charging_power_kw, soc_current, hora_regreso,
           pre_computed_inicio_ventana=pre_computed,
       )
       ```
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Per-trip loop uses batch-computed inicio_ventana
  - **Verify**: `grep -n "pre_computed_inicio_ventana" custom_components/ev_trip_planner/emhass_adapter.py | grep "await self._populate" | head -1`
  - **Commit**: `feat(sequential-trip): pass batch inicio_ventana to per-trip cache entry`
  - _Requirements: FR-1, FR-6_
  - _Design: Component 1, Data Flow step 3-4_

- [ ] 1.8 [VERIFY] Phase 0 failing test now passes
  - **Do**: Run the test from task 0.1 — it should now PASS
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "sequential_trips_def_start" 2>&1 | tail -5`
  - **Done when**: Test passes (bug is fixed)

- [ ] 1.9 [VERIFY] Quality checkpoint: type check + lint + all existing tests pass
  - **Do**: Run mypy, ruff, and full test suite
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ -x`
  - **Done when**: No type errors, no lint errors, all tests pass
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after core fix`

## Phase 2: Comprehensive Tests

Add test coverage for edge cases and integration scenarios.

- [ ] 2.1 Write test: single trip backward compatibility (def_start_timestep = 0)
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with 1 trip and `return_buffer_hours=4.0`
    2. Assert `len(results) == 1`
    3. Assert `results[0]["inicio_ventana"] == hora_regreso`
    4. Verify def_start_timestep remains 0 for single trip scenario
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "single_trip_backward" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify single trip backward compatibility`
  - _Requirements: FR-5, AC-1.3_
  - _Design: Test Coverage Table row 2_

- [ ] 2.2 Write test: three sequential trips with cumulative offsets
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with 3 trips
    2. Assert `inicio_ventana[i]` follows sequential chaining with buffer
    3. Assert cumulative offset: trip 2 starts after trip 1 arrival + buffer
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "three_sequential" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify 3-trip cumulative offset`
  - _Requirements: FR-2, AC-1.2_
  - _Design: Test Coverage Table row 3_

- [ ] 2.3 Write test: window_start capped at deadline when buffer exceeds gap
  - **Do**:
    1. Create 2 trips with tight gap
    2. Set return_buffer_hours that would push window_start past deadline
    3. Assert result still returns valid window (not crash)
    4. Assert inicio_ventana does not exceed fin_ventana
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "window_capped" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify window capped at deadline edge case`
  - _Requirements: FR-2_
  - _Design: Error Handling table_

- [ ] 2.4 Write test: def_end_timestep unchanged after fix (AC-1.4)
  - **Do**:
    1. Compare def_end_timestep values from single-trip vs batch computation
    2. Assert def_end_timestep values are identical
    3. Ensure the fix only affects def_start_timestep
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "end_timestep_unchanged" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify def_end_timestep unchanged`
  - _Requirements: AC-1.4_
  - _Design: Test Coverage Table row 7_

- [ ] 2.5 Write test: empty trips list returns empty result
  - **Do**:
    1. Test `calculate_multi_trip_charging_windows` with `trips=[]`
    2. Assert returns empty list
    3. Assert no crash or exception
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "empty_trips" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify empty trips edge case`
  - _Design: Error Handling table_

- [ ] 2.6 Write test: two trips with 0 buffer start consecutively
  - **Do**:
    1. Test `return_buffer_hours=0.0`
    2. Assert trip 2 starts exactly at trip 1 arrival (no gap)
    3. Verify consecutive windows with no buffer
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "zero_buffer" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): verify 0 buffer consecutive trips`
  - _Design: Edge Cases_

- [ ] 2.7 Write EMHASSAdapter batch processing integration test
  - **Do**:
    1. Create mock EMHASSAdapter with 2 trips
    2. Stub `_get_current_soc` to return 50.0
    3. Stub `_get_hora_regreso` to return known datetime
    4. Call `async_publish_all_deferrable_loads` with 2 trips
    5. Assert `_cached_per_trip_params[trip0_id]["def_start_timestep"] == 0`
    6. Assert `_cached_per_trip_params[trip1_id]["def_start_timestep"] > 0`
  - **Files**: `tests/test_charging_window.py`
  - **Done when**: Test exists and passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -v -k "batch_processing" 2>&1 | tail -5`
  - **Commit**: `test(sequential-trip): add EMHASSAdapter batch processing integration test`
  - _Requirements: FR-1, AC-1.1_
  - _Design: Test Coverage Table row 5_

- [ ] 2.8 [VERIFY] Quality checkpoint: all tests pass + lint + type check
  - **Do**: Run full test suite, lint, and type check
  - **Verify**: `PYTHONPATH=. .venv/bin/mypy custom_components/ev_trip_planner/ --no-namespace-packages && ruff check custom_components/ev_trip_planner/ && PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Done when**: All tests pass, no lint errors, no type errors
  - **Commit**: `chore(sequential-trip): pass quality checkpoint after Phase 2 testing`

## Phase 3: Quality Gates

All local checks must pass. Create PR and verify CI.

- [ ] 3.1 Run full test suite to verify zero regressions
  - **Do**: Run complete pytest suite
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Done when**: All 1519+ tests pass with zero failures

- [ ] 3.2 Run make check (full CI: test + lint + mypy)
  - **Do**: Run the project's check target
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && PYTHONPATH=. make check`
  - **Done when**: test + lint + mypy all pass
  - **Commit**: `chore(sequential-trip): pass full local CI` (if fixes needed)

- [ ] 3.3 [VERIFY] AC checklist
  - **Do**: Programmatically verify each acceptance criteria:
    1. AC-1.1: Run sequential offset test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "sequential_trips_def_start"`
    2. AC-1.2: Run 3-trip test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "three_sequential"`
    3. AC-1.3: Run single trip test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "single_trip_backward"`
    4. AC-1.4: Run end_timestep test `PYTHONPATH=. .venv/bin/python -m pytest tests/test_charging_window.py -k "end_timestep_unchanged"`
    5. AC-1.5: `grep -c "p_deferrable_matrix" custom_components/ev_trip_planner/emhass_adapter.py` (verify no changes to matrix generation)
  - **Verify**: All test commands exit 0 AND grep returns expected count
  - **Done when**: All 5 acceptance criteria confirmed met via automated checks

- [ ] 3.4 [VERIFY] PR opened correctly
  - **Do**:
    1. Verify current branch: `git branch --show-current`
    2. Push branch: `git push -u origin feat/fix-sequential-trip-charging`
    3. Create PR with summary of changes
    4. Verify PR exists: `gh pr view --json url,state`
  - **Done when**: PR exists on GitHub with state OPEN

## Notes

- **Constant only**: RETURN_BUFFER_HOURS = 4.0 is immutable for MVP. No config_flow changes needed.
- **duration_hours preserved**: The existing parameter represents trip duration (how long car is away). It is NOT renamed.
- **return_buffer_hours is NEW**: Added as a separate parameter to calculate_multi_trip_charging_windows() for the gap between trips.
- **No sensor.py changes needed**: Aggregation already correct, bug is in cache population.
- **Key invariant**: p_deferrable_matrix and def_end_timestep_array must remain unchanged.
- **hora_regreso is dynamic**: Already handled by presence_monitor for early returns. No changes needed.
