# Tasks: Propagate Charge Deficit Algorithm

Add `calculate_hours_deficit_propagation()` to `calculations.py` — backward propagation of unmet charging hours across chained trips.

## Tasks

### 1: Write `calculate_hours_deficit_propagation()` in `calculations.py`

Implement the pure function that walks backward through charging windows and propagates deficit to earlier trips with spare capacity.

- [x] 1.1 [CODE] Add function to `custom_components/ev_trip_planner/calculations.py`
  - **Do**:
    1. Read `custom_components/ev_trip_planner/calculations.py` lines 530-540 (end of `calculate_multi_trip_charging_windows`)
    2. Add new function `calculate_hours_deficit_propagation()` after `calculate_multi_trip_charging_windows()`, following existing code patterns
    3. Implement the algorithm:
       - Walk backward from last trip to first
       - For each trip: `own_deficit = max(0, horas_carga_necesarias - ventana_horas)`
       - `spare = max(0, ventana_horas - def_total_hours)`
       - `absorbed = min(deficit_carrier, spare)` where deficit_carrier accumulates deficits
       - `deficit_carrier = deficit_carrier - absorbed + own_deficit`
       - Store: `deficit_hours_propagated` (absorbed from next), `deficit_hours_to_propagate` (remaining carrier), `adjusted_def_total_hours` (original + absorbed)
    4. Handle edge cases: empty input → [], single trip → all deficit on to_propagate
    5. Round all propagation values to 2 decimal places
    6. Do NOT modify `calculate_multi_trip_charging_windows()` — it stays unchanged
  - **Files**: `custom_components/ev_trip_planner/calculations.py` (append new function)
  - **Done when**: Function exists, is importable, and returns correct enriched window dicts
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && python -c "from custom_components.ev_trip_planner.calculations import calculate_hours_deficit_propagation; print('IMPORT_OK')"`
  - **Commit**: `feat(calculations): add backward charge deficit propagation function`

### 2: Add unit tests to `tests/test_calculations.py`

Create `TestCalculateHoursDeficitPropagation` test class covering all scenarios.

- [ ] 2.1 [TEST] Write test class with comprehensive scenarios
  - **Do**:
    1. Read `tests/test_calculations.py` to find where other test classes are defined
    2. Add `TestCalculateHoursDeficitPropagation` class with these test methods:
       - `test_no_deficit_all_trips_sufficient` — 3 trips, all windows ≥ required hours
       - `test_last_trip_deficit_absorbed` — trip #3 needs 3h, has 2h window; trip #2 has 4h spare
       - `test_chain_propagation` — trip #3 deficit 3h, trip #2 spare 2h, trip #1 spare 4h (partial absorption on trip #1)
       - `test_single_trip_deficit` — 1 trip, needs 5h, has 2h window → deficit stays on to_propagate
       - `test_empty_input` — [] → []
       - `test_deficit_hours_propagated_is_not_cumulative` — verify absorbed from next trip only
       - `test_ventana_horas_unchanged` — assert ventana_horas equals input for every returned dict
       - `test_adjusted_def_total_hours_correct` — assert adjusted = original + propagated
    3. Use `calculate_multi_trip_charging_windows()` to generate realistic window dicts for input
    4. Import `determine_charging_need` from `calculations.py` to build `def_total_hours` list
    5. Each test must assert specific numeric values, not just presence of keys
  - **Files**: `tests/test_calculations.py`
  - **Done when**: All 8 test methods pass with green output
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && python -m pytest tests/test_calculations.py::TestCalculateHoursDeficitPropagation -v && echo TESTS_PASS`
  - **Commit**: `test(calculations): add tests for charge deficit propagation`

### 3: Verify existing tests unchanged

Run existing test suites to confirm no regression.

- [ ] 3.1 [VERIFY] Run multi-trip charging windows tests
  - **Do**: Run `pytest tests/test_calculations.py -k "multi_trip" -v`
  - **Done when**: All multi-trip tests pass
  - **Commit**: None

- [ ] 3.2 [VERIFY] Run SOC deficit propagation tests
  - **Do**: Run `pytest tests/test_calculations.py -k "deficit" -v`
  - **Done when**: All deficit propagation tests pass
  - **Commit**: None

- [ ] 3.3 [VERIFY] Run full calculations test suite
  - **Do**: Run `python -m pytest tests/test_calculations.py -v --tb=short`
  - **Done when**: All tests in test_calculations.py pass
  - **Commit**: None

## Execution Order
1 → 2 → 3 (implementation → tests → verification)

## Notes
- `def_total_hours` in window dicts comes from `determine_charging_need()` which returns `ceil(kwh_needed / charging_power_kw)`
- If `def_total_hours` not provided, default to `horas_carga_necesarias` from the window dict
- `spare capacity = ventana_horas - def_total_hours` (floored at 0)
- Propagation is strictly backward — last trip first, no cycles
- First trip has no predecessor, so remaining deficit stays on `deficit_hours_to_propagate`
- The function is pure — no I/O, no state mutation
