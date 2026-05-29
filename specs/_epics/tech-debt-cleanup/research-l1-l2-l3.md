# Research: Layers 1, 2, 3 -- Technical Debt Cleanup

## Layer 1: Test Execution

### Pytest Results
- **Total tests collected: 1849** (1848 passed, 1 skipped)
- **Test collection time: 0.45s**
- **Runtime: 7.90s**
- **Python version: 3.14.3**

### Test File Distribution
- **~100 Python test files** in `tests/` (flat structure, no subdirectories except e2e/)
- **45 tests** in `tests/test_init.py`
- **9 tests** in `tests/test_missing_coverage.py`
- **1849 total test items** collected

### Coverage
- **Current coverage: 100.0%** across all 18 source files
- **Total statements: 4,927**, all covered
- pytest runs with `--cov-fail-under=100` -- currently passing

### Mutation Testing
- **Configuration:** `pyproject.toml` `[tool.mutmut]`
  - `paths_to_mutate = ["custom_components/ev_trip_planner"]`
  - `runner = "pytest"`
  - `tests_dir = ["tests/"]`
  - `timeout = 600`
- **Quality gate config:** `[tool.quality-gate.mutation]`
  - `global_kill_threshold = 0.48` (current baseline)
  - `target_final = 1.00` (aiming for 100% mutation kill rate)
  - `modules_per_sprint = 2`
- **Per-module targets:**
  - `calculations`: kill_threshold = 0.71, status = "passing"
  - `utils`: kill_threshold = 0.89, status = "passing"
- **Checkpoint states:** 17/17 modules passing (from quality-gate-checkpoint.json)

### E2E Tests
- **10 e2e spec files total:**
  - `tests/e2e/`: 7 files (create-trip, delete-trip, edit-trip, form-validation, panel-emhass-sensor-entity-id, trip-list-view, zzz-integration-deletion-cleanup, emhass-sensor-updates)
  - `tests/e2e-dynamic-soc/`: 2 files (test-config-flow-soh, test-dynamic-soc-capping)
- **30 e2e tests** passed (per checkpoint)
- E2E uses `hass` directly on `localhost:8123` (no Docker)
- E2E command: `./scripts/run-e2e.sh`

### Test Configuration
- Single `conftest.py` at `tests/conftest.py` (~700 lines)
- Contains: `mock_datetime_2026_05_04_monday_0800_utc` factory fixture, `enable_custom_integrations`, `mock_frame_reporting` (autouse), `mock_hass`, `mock_store`, `trip_manager_with_entry_id`, `trip_manager_no_entry_id`
- `asyncio_mode = "auto"` in pyproject.toml

### Excluded Test Directory
- `tests_excluded_from_mutmut/` contains 2 files: `test_timezone_utc_vs_local_bug.py`, `test_vehicle_controller_event.py`

---

## Layer 2: Test Quality

### Weak Assertions (assert True / assert 1 == 1)
- **2 `assert True` violations:**
  1. `tests/test_init.py:831` -- `assert True, "Placeholder implementation - cleanup not yet active"` (placeholder for unimplemented feature)
  2. `tests/test_missing_coverage.py:550` -- `assert True` (genuine weak test)
- **2 `sleep(0)` calls in tests:**
  1. `tests/test_trip_calculations.py:50` -- `await asyncio.sleep(0)` (simulating async)
  2. `tests/test_trip_calculations.py:56` -- `await asyncio.sleep(0)` (simulating async)

### Test File Organization
- **Flat structure:** All test files in `tests/` root (no module-to-file mapping)
- No tests organized by source module (e.g., no `tests/test_trip_manager/` subdirectory)
- Naming convention: `test_<module>.py` for most modules, but several tests are feature-specific (e.g., `test_emhass_publish_bug.py`, `test_config_flow_issues.py`)
- Duplicate-like naming: `test_config_flow.py`, `test_config_flow_core.py`, `test_config_flow_milestone3.py`, `test_config_flow_milestone3_1_ux.py`, `test_config_flow_missing.py`, `test_config_flow_issues.py`

### Test Duplication
- **~299 similar test pairs** detected (per checkpoint)
- Multiple test files with "missing coverage" naming pattern: `test_missing_coverage.py`, `test_coverage_remaining.py`, `test_coverage_100_percent.py`, `test_coverage_edge_cases.py`, `test_dashboard_cover.py`, `test_dashboard_missing.py`, `test_dashboard_cover.py`, `test_dashboard_validation.py`, `test_dashboard_missing.py`, `test_dashboard_cover.py`
- Multiple test files per module: `test_trip_manager.py`, `test_trip_manager_core.py`, `test_trip_manager_more_coverage.py`, `test_trip_manager_missing_coverage.py`, `test_trip_manager_cover_line1781.py`, `test_trip_manager_power_profile.py`, `test_trip_manager_datetime_tz.py`, `test_trip_manager_fix_branches.py`, `test_trip_manager_entry_lookup.py`, `test_trip_manager_emhass.py`, `test_trip_manager_calculations.py`, `test_trip_manager_sensor_hooks.py`

### Test Coverage Files
- `coverage.json`: Last generated 2026-04-21, from `feature-soh-soc-cap` branch vs `main` base
- `quality-gate-checkpoint.json`: Last updated 2026-05-06, from `feature-soh-soc-cap` branch vs `main` base
  - Layer 1: PASS (tests, coverage, mutation, e2e all passing)
  - Layer 2: FAIL (weak test detection)
  - Layer 3: FAIL (linting, formatting, pyright, SOLID)

---

## Layer 3: Code Quality

### Ruff Check
- **1 error** (fixable): F841 unused variable `captured_async_add_entities` in `tests/test_entity_registry.py:151`
- Note: The checkpoint shows 1 error, but current `ruff check .` returns "All checks passed!" -- the error may have already been fixed

### Ruff Format
- **15 files need formatting** (7 would be reformatted, rest already formatted):
  - `_bmad/core/skills/bmad-distillator/scripts/analyze_sources.py`
  - `_bmad/core/skills/bmad-distillator/scripts/tests/test_analyze_sources.py`
  - `custom_components/ev_trip_planner/calculations.py`
  - `custom_components/ev_trip_planner/emhass_adapter.py`
  - `tests/test_config_updates.py`
  - `tests_excluded_from_mutmut/test_timezone_utc_vs_local_bug.py`
  - `tests_excluded_from_mutmut/test_vehicle_controller_event.py`

### Pyright (Type Checking)
- **16 errors, all in `sensor.py`** -- `reportIncompatibleVariableOverride`
  - 4 sensor classes (`TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripSensor`, `TripEmhassSensor`) each have 4 errors:
    - `available` incompatible override
    - `native_value` override (property vs cached_property)
    - `extra_state_attributes` override (property vs cached_property)
    - `device_info` override (property vs cached_property)
  - These are **known pre-existing** Home Assistant Entity type compatibility issues, not introduced by this branch

### SOLID Violations

#### SRP (Single Responsibility Principle)
- **`EMHASSAdapter`**: 8 public methods, ~426 LOC (class itself is fine, but has high arity helper methods)
- **`TripManager`**: 4 public methods, ~234 LOC
- **`PresenceMonitor`**: 3 public methods, ~244 LOC

#### High-Arity Functions (>7 args)
- `calculate_multi_trip_charging_windows(9 args)` -- `calculations.py`
- `calculate_deficit_propagation(9 args)` -- `calculations.py`
- `calculate_power_profile_from_trips(8 args)` -- `calculations.py`
- `calculate_power_profile(8 args)` -- `calculations.py`
- `DashboardImportResult.__init__(8 args)` -- `dashboard.py`
- `_populate_per_trip_cache_entry(12 args)` -- `emhass_adapter.py`

#### LOC by File
| File | LOC |
|------|-----|
| emhass_adapter.py | 2,729 |
| trip_manager.py | 2,502 |
| calculations.py | 1,690 |
| services.py | 1,631 |
| dashboard.py | 1,279 |
| config_flow.py | 1,038 |
| sensor.py | 1,019 |
| presence_monitor.py | 794 |
| vehicle_controller.py | 525 |

### Antipatterns (per checkpoint)
- Tier A antipatterns: 0
- Tier B antipatterns: 0
- Principles (DRY, KISS, YAGNI, LoD, CoI): all PASS

### `pragma: no cover` Locations
- **Total: 273 locations** across 10 files
- Distribution:
  - `trip_manager.py`: 33 (IO error paths, filesystem access)
  - `presence_monitor.py`: 22 (IO error paths)
  - `vehicle_controller.py`: 19 (IO error paths)
  - `sensor.py`: 18 (HA entity setup error paths)
  - `dashboard.py`: 18 (IO error paths)
  - `emhass_adapter.py`: 13 + 7 (debug/error paths)
  - `calculations.py`: 10
  - `services.py`: 9 + 6 (error paths)
  - `schedule_monitor.py`: 6
  - `config_flow.py`: 1

### TODO/FIXME/BUG Comments in Source
- **16 DEBUG/E2E-DEBUG comments** in `coordinator.py` (debug logging, not actual TODOs)
- **1 TODO** in `config_flow.py:177`: "Make EMHASS config path configurable"
- **1 TODO** in `schedule_monitor.py:188`: "Implement proper schedule parsing"
- Multiple "BUG FIX" comments in `emhass_adapter.py` (documented fixes, not active issues)

---

## Summary: What Needs Fixing

### In-branch fixable (immediate):
1. **`assert True` in `tests/test_missing_coverage.py:550`** -- replace with real assertion
2. **1 file with ruff format issues** in custom_components: `calculations.py`, `emhass_adapter.py`

### Pre-existing (out of scope for individual branches):
1. **16 pyright errors** in `sensor.py` -- HA Entity type overrides, requires HA version bump or type: ignore
2. **9 SOLID Tier A violations** -- EMHASSAdapter SRP, high-arity functions
3. **273 `pragma: no cover`** locations -- IO error paths that are hard to test
4. **1790 weak test A1 violations** -- known coverage test pattern (smoke tests)
5. **~299 similar test pairs** -- test duplication across many files
6. **Flat test organization** -- ~100 test files in root directory
7. **7 files needing ruff format** -- including 2 in `tests_excluded_from_mutmut/`

### Current State Scores (per quality-gate-checkpoint.json):
| Layer | Status | Key Metric |
|-------|--------|------------|
| Layer 1 | PASS | 1848 tests, 100% coverage, 17/17 mutation modules passing |
| Layer 2 | FAIL | 1790 weak tests, 299 similar pairs |
| Layer 3 | FAIL | 16 pyright errors, 9 SOLID violations, 273 pragma no-cover, 7 format issues |
