# Tasks: PR #35 Review Fixes

Three surgical fixes from PR #35 review: move runtime_data assignment before publish, add warning log before total_hours cap, and fix startup_penalty type from `true` to `0.0` in Jinja2 template.

## Tasks

### 1: Fix startup_penalty type (Bug #13) [MEDIUM — highest behavioral risk]

Fixes Jinja2 template sending boolean `true` instead of numeric `0.0` to EMHASS, which can cause type errors in the optimizer.

- [x] 1.1 [FIX] Change startup_penalty value from `true` to `0.0` in panel.js
  - **Do**:
    1. Read `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/frontend/panel.js` line 977
    2. Change the Jinja2 expression so `set_deferrable_startup_penalty` sends `0.0` (number) instead of `true` (boolean) when `number_of_deferrable_loads` is 0
    3. Apply three changes to line 977:
       - Replace `true` with `0.0` in the final `default()` call argument
       - Remove extra space before the colon (`set_deferrable_startup_penalty ` → `set_deferrable_startup_penalty`)
       - Add `| int(0)` filter to the `state_attr()` call for `number_of_deferrable_loads` to ensure numeric type
    4. Verify no other `true` values are sent where numbers are expected in the same template block
  - **Files**: `custom_components/ev_trip_planner/frontend/panel.js` (line ~977)
  - **Done when**: Line 977 sends `0.0` not `true` as default for `set_deferrable_startup_penalty`
  - **Verify**: `grep -n 'set_deferrable_startup_penalty' /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/frontend/panel.js | grep '0\\.0' && echo BUG13_FIX_PASS`
  - **Commit**: `fix(fixes): change startup_penalty true to 0.0 in panel.js`
  - _Requirements: Bug #13 from PR #35 review_

### 2: Add logging before total_hours cap (Bug #12) [LOW]

Adds warning log when total_hours is capped to window_size — helps debug trips that get truncated.

- [x] 2.1 [FIX] Add _LOGGER.warning before total_hours cap in emhass_adapter.py
  - **Do**:
    1. Read `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/emhass_adapter.py` around line 639
    2. Insert a `_LOGGER.warning()` call immediately before `total_hours = window_size` (line 640)
    3. Follow the existing log pattern in this file: `_LOGGER.warning("Capping total_hours from %.1f to window size %.1f for trip %s", old_total, window_size, trip_id)`
    4. Capture the old value into a variable before reassignment: `old_total_hours = total_hours` then log, then assign `total_hours = window_size`
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py` (~lines 639-640)
  - **Done when**: Warning log fires before capping, includes old value, window size, and trip_id
  - **Verify**: `grep -n '_LOGGER.warning.*Capping\|_LOGGER.warning.*cap' /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/emhass_adapter.py && echo BUG12_FIX_PASS`
  - **Commit**: `fix(fixes): add warning log before total_hours cap in emhass_adapter.py`
  - _Requirements: Bug #12 from PR #35 review_

### 3: Move runtime_data assignment before publish (Bug #4) [MEDIUM]

Fixes potential None reference — `runtime_data` is used on line 175 but assigned on line 164, while `publish_deferrable_loads()` on line 160 may need it.

- [x] 3.1 [FIX] Reorder runtime_data assignment in __init__.py
  - **Do**:
    1. Read `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/__init__.py` lines 155-180
    2. Move the `entry.runtime_data = EVTripRuntimeData(...)` block (lines 163-168) to before `await trip_manager.publish_deferrable_loads()` (line 160)
    3. New order:
       - Block A (new position): `entry.runtime_data = EVTripRuntimeData(...)`
       - Block B: `if emhass_adapter is not None: await trip_manager.publish_deferrable_loads()`
       - Block C: `await async_register_panel_for_entry(...)`
    4. Verify `runtime_data = entry.runtime_data` on line 175 still works (it will, since runtime_data is now set earlier)
  - **Files**: `custom_components/ev_trip_planner/__init__.py` (~lines 160-168)
  - **Done when**: runtime_data is assigned before publish_deferrable_loads() call
  - **Verify**: `grep -n 'runtime_data = EVTripRuntimeData' /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/__init__.py > /tmp/line_a.txt && grep -n 'publish_deferrable_loads' /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/__init__.py > /tmp/line_b.txt && awk '{print $1}' /tmp/line_a.txt < /tmp/line_b.txt | head -1 | while read a b; do [ "$a" -lt "$b" ] && echo BUG4_FIX_PASS; done`
  - **Commit**: `fix(fixes): move runtime_data assignment before publish_deferrable_loads in __init__.py`
  - _Requirements: Bug #4 from PR #35 review_

### 4: Verify with existing tests (all bugs)

Run the full test suite to confirm no regressions from the three fixes.

- [x] 4.1 [VERIFY] Run full test suite
  - **Do**: Run pytest across the entire test directory. This takes ~3-5 minutes for 1631 tests.
  - **Files**: N/A (read-only verification)
  - **Done when**: All tests pass with exit code 0
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && python -m pytest tests/ --tb=short 2>&1 | tail -20 && echo ALL_TESTS_PASS`
  - **Commit**: None

- [x] 4.2 [VERIFY] Run targeted tests for changed files
  - **Do**: Run tests specific to each changed module for faster feedback and explicit coverage.
  - **Files**: N/A (read-only verification)
  - **Done when**: All targeted tests pass
  - **Verify**: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && python -m pytest tests/test_init.py tests/test_emhass_adapter.py tests/test_emhass_adapter_def_end_bug.py tests/test_trip_manager_core.py --tb=short 2>&1 | tail -10 && echo TARGETED_TESTS_PASS`
  - **Commit**: None

- [x] 4.3 [VERIFY] Verify Python syntax of modified files
  - **Do**: Syntax-check the two Python files that were modified.
  - **Files**: N/A (read-only verification)
  - **Done when**: No syntax errors
  - **Verify**: `python -m py_compile /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/__init__.py && python -m py_compile /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/emhass_adapter.py && echo SYNTAX_PASS`
  - **Commit**: None

## Execution Order
1 → 2 → 3 → 4 (highest behavioral risk first, then verification)

## Notes
- POC shortcuts: N/A — these are direct fixes, no prototyping needed
- Production TODOs: None — each fix is complete as specified
- No files overlap between tasks 1, 2, 3 — each touches a different file
- Risk assessment: Task 1 (JavaScript template) is highest risk because it changes runtime data types; tasks 2 and 3 are low-risk code reordering/logging
- The `| int(0)` filter on line 977 ensures Home Assistant's template engine always produces a number, not null
