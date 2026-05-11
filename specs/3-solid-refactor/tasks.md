# Tasks: 3-solid-refactor

## Overview

Total tasks: 155

**Workflow**: TDD Red-Green-Yellow (intent = REFACTOR per requirements.md scope).

1. Phase 1: Red-Green-Yellow Cycles — 9 god modules decomposed via [RED]→[GREEN]→[YELLOW] triplets
2. Phase 2: Additional Testing — property-based regression test for BUG-001/002 invariants
3. Phase 3: Quality Gates — full local CI (V4), CI pipeline (V5), AC checklist (V6), VE0..VE3
4. Phase 4: PR Lifecycle — autonomous CI monitoring + review resolution

## Completion Criteria (Autonomous Execution Standard)

This spec is not complete until ALL criteria are met:

✅ **Zero Regressions**: All 1,820+ existing tests pass
✅ **Modular & Reusable**: Every file ≤ 500 LOC; every class ≤ 20 public methods; LCOM4 ≤ 2; verb diversity ≤ 5 (with documented allowlists)
✅ **Real-World Validation**: `make e2e` (30 tests on :8123) + `make e2e-soc` (10 tests) + staging VE2 flow all green
✅ **All Tests Pass**: Unit, integration, E2E all green; 100% coverage maintained
✅ **CI Green**: GitHub Actions all green
✅ **PR Ready**: PR open against `epic/tech-debt-cleanup` with all checks ✓
✅ **Review Comments Resolved**: All code review feedback addressed
✅ **Bar A (NFR-7.A)**: solid_metrics 5/5 PASS, 0 Tier A antipatterns, 0 lint-imports violations, 0 pyright errors, 0 DRY/KISS violations

> **Quality Checkpoints**: V-checkpoints inserted after each god-module decomposition (V1..V12 = per-package); final-sequence checkpoints (V_final_a/b/c) in Phase 3.

## Phase 1: Red-Green-Yellow Cycles (TDD Workflow)

Focus: Each god module decomposed via [RED]→[GREEN]→[YELLOW] triplets.

**Decomposition order** (dependency-first, per design.md §6.2):
calculations → vehicle → dashboard → emhass → trip → services → sensor → config_flow → presence_monitor

**Step 0.5 pre-flight** (per design.md §6.1 + §6.2):
- DRY consolidation (tasks 1.7-1.8): `validate_hora`, `is_trip_today` → `utils.py`; `calculate_day_index` → `calculations/core.py` (canonical, no `utils.py` copy)
- lint-imports config fix (tasks 1.2-1.4): `[tool.import-linter]` → `[tool.importlinter]` + 7 contracts
- ISP check implementation (tasks 1.5-1.6): `solid_metrics.py max_unused_methods_ratio` per AC-4.7
- Dashboard `__file__` pre-condition (tasks 1.38-1.41): pathlib-based `TEMPLATES_DIR` (per design.md §6.1 — NOT `os.path.join`)

Each god-module decomposition ends with a Vn checkpoint that runs `ruff check && pyright && make test && make e2e && make e2e-soc`.

- [x] 1.1 [VERIFY] Run baseline quality-gate: capture baseline metrics
  - **Do**:
    1. Run `make quality-gate` and capture full output
    2. Write baseline metrics to chat.md with `[BASELINE-XXX]` tags
    3. Record baseline commit hash (radon is NOT installed here — it is installed in task 3.0, the canonical Tier-A tooling install task)
  - **Files**: .progress.md (baseline section), chat.md
  - **Done when**: Baseline captured with all 8 quality-gate script outputs
  - **Verify**: `make quality-gate > /tmp/baseline.txt 2>&1 && test -s /tmp/baseline.txt && echo BASELINE_PASS`
  - **Commit**: `chore(spec3): capture quality-gate baseline before refactoring`
  - _Requirements: NFR-7.B.1, NFR-8_
  - _Design: §7 (Per-Decomposition Validation Gate)_

- [x] 1.2 [RED] Test: lint-imports uses correct `[tool.importlinter]` key
  - **Do**: Write a shell-test asserting that pyproject.toml contains `[tool.importlinter]` (no hyphen). Current file has `[tool.import-linter]` which is ignored.
  - **Files**: tests/unit/test_importlinter_config.py
  - **Done when**: Test exists and fails (current config uses hyphenated key)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_importlinter_config.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - lint-imports must use [tool.importlinter] not [tool.import-linter]`
  - _Requirements: FR-3.5_
  - _Design: §4.4 (lint-imports Contracts TOML)_

- [x] 1.3 [GREEN] Replace `[tool.import-linter]` with `[tool.importlinter]` and add 7 contracts
  - **Do**:
    1. Remove `[tool.import-linter]` block from pyproject.toml
    2. Add `[tool.importlinter]` with `root_package = "custom_components.ev_trip_planner"`
    3. Add 7 contracts per design.md §4.4: independence, trip->sensor forbidden, presence_monitor->trip forbidden, dashboard->trip/emhass/services forbidden, calculations leaf forbidden, calculations independence supplement, layered architecture
    4. Update `make import-check` Makefile target to include `lint-imports --config pyproject.toml`
  - **Files**: pyproject.toml, Makefile
  - **Done when**: `[tool.import-linter]` removed, `[tool.importlinter]` present with 7 contracts, `make import-check` calls lint-imports
  - **Verify**: `grep -q '\[tool.importlinter\]' pyproject.toml && grep -c '\[\[tool.importlinter.contracts\]\]' pyproject.toml | grep -q '^7$' && echo GREEN_PASS`
  - **Commit**: `fix(spec3): correct import-linter key to [tool.importlinter] and add 7 contracts`
  - _Requirements: FR-3.5, NFR-1.5_
  - _Design: §4.4 (lint-imports Contracts TOML)_

- [x] 1.4 [YELLOW] Verify lint-imports config syntax only (contract enforcement deferred)
  - **Do**:
    1. Verify pyproject.toml has `[tool.importlinter]` with 7 contract blocks (structural check)
    2. Verify `ruff check --select I` passes (import style, independent of packages)
    3. NOTE: `lint-imports --config pyproject.toml` contract enforcement is deferred to Phase 2 (task 2.5) because the 7 contracts reference packages (trip/, sensor/, emhass/, etc.) that are created during SOLID decomposition. Running `make import-check` now would always FAIL.
  - **Files**: pyproject.toml, Makefile
  - **Done when**: Importlinter config is syntactically valid, ruff import style passes
  - **Verify**: `grep -q '\[tool.importlinter\]' pyproject.toml && grep -c '\[\[tool.importlinter.contracts\]\]' pyproject.toml | grep -q '^7$' && .venv/bin/ruff check --select I custom_components/ tests/ && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): validate lint-imports config syntax (contract enforcement deferred to Phase 2)`
  - _Requirements: FR-3.5, NFR-1.5_
  - _Design: §4.4 (lint-imports Contracts TOML)_



- [x] 1.5 [RED] Test: solid_metrics.py implements max_unused_methods_ratio ISP check
  - **Do**: Write a test that asserts `scripts/solid_metrics.py` contains `max_unused_methods_ratio` logic (AST walk + stub detection for ABC methods). Current code has no such check.
  - **Files**: tests/unit/test_solid_metrics_isp.py
  - **Done when**: Test exists and fails (check not implemented yet)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_solid_metrics_isp.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - solid_metrics.py must implement max_unused_methods_ratio`
  - _Requirements: AC-4.7, NFR-1.4_
  - _Design: §2 (ISP mechanism)_

- [x] 1.6 [GREEN] Implement max_unused_methods_ratio in solid_metrics.py (~60-100 LOC)
  - **Do**:
    1. Add AST walk to detect ABC/Protocol definitions in `custom_components.ev_trip_planner/`
    2. Skip HA framework ABCs (Entity, RestoreEntity, Platform, ConfigFlow, OptionsFlow)
    3. For each intra-package ABC, count abstract methods with stub bodies (`pass`, `...`, `raise NotImplementedError`)
    4. Compute ratio = stubs / total abstract methods per ABC
    5. Fail if ratio > 0.5 for any ABC
  - **Files**: scripts/solid_metrics.py
  - **Done when**: Test from 1.5 passes; `solid_metrics.py` reports ISP check results
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_solid_metrics_isp.py -v && echo GREEN_PASS`
  - **Commit**: `feat(spec3): implement max_unused_methods_ratio ISP check in solid_metrics.py`
  - _Requirements: AC-4.7, NFR-1.4_
  - _Design: §2 (ISP mechanism)_


- [x] 1.7 [P] DRY: Consolidate `validate_hora` into single canonical location
  - **Do**:
    1. Identify all duplicate `validate_hora` / `pure_validate_hora` copies
    2. Remove duplicates from god modules, import from `utils.py`
    3. Verify behavior unchanged by running affected tests
  - **Files**: custom_components/ev_trip_planner/*.py (duplicate removal), utils.py
  - **Done when**: `validate_hora` exists in exactly one location (`utils.py` as `pure_validate_hora`)
  - **Verify**: `grep -rn 'def validate_hora\|def pure_validate_hora' custom_components/ev_trip_planner/ --include='*.py' | grep -v 'utils.py' | grep -v '__pycache__' | grep -v '^Binary' | wc -l | grep -q '^0$' && echo GREEN_PASS`
  - **Commit**: `fix(spec3): consolidate validate_hora into utils.py canonical location`
  - _Requirements: AC-5.1, NFR-2.1_
  - _Design: §6.2 Step 0.5 (DRY consolidation pre-flight)_

- [x] 1.8 [P] DRY: Consolidate `is_trip_today` into single canonical location
  - **Do**:
    1. Identify all duplicate `is_trip_today` / `pure_is_trip_today` copies
    2. Remove duplicates from god modules, import from `utils.py`
    3. Verify behavior unchanged
  - **Files**: custom_components/ev_trip_planner/*.py (duplicate removal), utils.py
  - **Done when**: `is_trip_today` exists in exactly one location
  - **Verify**: `grep -rn 'def is_trip_today\|def pure_is_trip_today' custom_components/ev_trip_planner/ --include='*.py' | grep -v 'utils.py' | grep -v '__pycache__' | grep -v '^Binary' | wc -l | grep -q '^0$' && echo GREEN_PASS`
  - **Commit**: `fix(spec3): consolidate is_trip_today into utils.py canonical location`
  - _Requirements: AC-5.2, NFR-2.1_
  - _Design: §6.2 Step 0.5 (DRY consolidation pre-flight)_


- [x] V1 [VERIFY] Quality check: ruff check && pyright
  - **Do**: Run quality checks
  - **Verify**: `ruff check . && make typecheck && python -m pylint custom_components/ && echo GREEN_PASS`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint pre-calculations`
  - _Requirements: NFR-7.A.5, NFR-8_
  - _Design: §7 (Per-decomposition validation gate, pre-calculations)_

### 1.1 calculations/ - Functional Decomposition + Bug Fixes

- [x] 1.9 [RED] Test: calculations package re-exports all 20 public names
  - **Do**: Write test that imports each of the 20 public names from `custom_components.ev_trip_planner.calculations` and asserts they resolve to callable/class/constant
  - **Files**: tests/unit/test_calculations_imports.py
  - **Done when**: Test exists and fails (package doesn't exist yet)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - calculations package must re-export all 20 public names`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.10 [GREEN] Scaffold calculations/ package with re-exports
  - **Do**:
    1. Create `custom_components/ev_trip_planner/calculations/` directory
    2. Create `__init__.py` with `from __future__ import annotations`, import all 20 names from sub-modules, declare `__all__`
    3. Create empty stub sub-modules: `core.py`, `windows.py`, `power.py`, `schedule.py`, `deficit.py`, `_helpers.py`
    4. Keep `calculations.py` unchanged (it's the authority)
    5. Add transitional shim: `calculations.py` re-exports from `calculations/`
  - **Files**: custom_components/ev_trip_planner/calculations/__init__.py, calculations/*.py, calculations.py (shim)
  - **Done when**: `from custom_components.ev_trip_planner.calculations import calculate_charging_window_pure` resolves; `make test` passes
  - **Verify**: `test -s custom_components/ev_trip_planner/calculations/__init__.py && python -c "from custom_components.ev_trip_planner.calculations import calculate_charging_window_pure, BatteryCapacity, ChargingDecision, DEFAULT_T_BASE" && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold calculations/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.11 [RED] Test: _ensure_aware and private helpers exist in _helpers.py
  - **Do**: Write test asserting `_helpers.py` exposes `_ensure_aware` and can be imported from `calculations._helpers`
  - **Files**: tests/unit/test_calculations_helpers.py
  - **Done when**: Test exists and fails (function not yet moved)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_helpers.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - _ensure_aware must exist in calculations._helpers`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_



- [x] 1.12 [GREEN] Move private helpers to `_helpers.py`
  - **Do**:
    1. Extract `_ensure_aware` and other private datetime helpers from `calculations.py` to `calculations/_helpers.py`
    2. Update `calculations.py` to import from `_helpers`
  - **Files**: custom_components/ev_trip_planner/calculations/_helpers.py, calculations.py
  - **Done when**: `_ensure_aware` importable from `calculations._helpers`; all existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_helpers.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move private helpers to calculations/_helpers.py`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.13 [RED] Test: core.py re-exports core types and functions
  - **Do**: Write test importing `BatteryCapacity`, `DEFAULT_T_BASE`, `calculate_dynamic_soc_limit`, `calculate_day_index`, `calculate_trip_time`, `calculate_charging_rate`, `calculate_soc_target` from `calculations.core`
  - **Files**: tests/unit/test_calculations_core.py
  - **Done when**: Test exists and fails (core.py not populated yet)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_core.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - calculations.core must export core types and functions`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_


- [x] 1.14 [GREEN] Move core types/functions to `core.py`
  - **Do**:
    1. Extract `BatteryCapacity`, `DEFAULT_T_BASE`, `calculate_dynamic_soc_limit`, `calculate_day_index`, `calculate_trip_time`, `calculate_charging_rate`, `calculate_soc_target` from `calculations.py` to `calculations/core.py`
    2. Update `calculations.py` to import from `calculations.core`
    3. Update `calculations/__init__.py` to re-export from `.core`
  - **Files**: custom_components/ev_trip_planner/calculations/core.py, calculations/__init__.py, calculations.py
  - **Done when**: All 7 names importable from `calculations.core`; existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_core.py tests/unit/test_calculations.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move core types and functions to calculations/core.py`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.15 [RED] Test: [BUG-001] ventana_horas uses departure not arrival
  - **Do**: Write test asserting `calculate_multi_trip_charging_windows` returns `ventana_horas == (fin_ventana - inicio_ventana) / 3600` (the invariant). Current code violates this (uses trip_arrival instead of trip_departure).
  - **Files**: tests/unit/test_ventana_horas_invariant.py
  - **Done when**: Test exists and fails with current code
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_ventana_horas_invariant.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - [BUG-001] ventana_horas invariant must hold (departure, not arrival)`
  - _Requirements: AC-10.1, AC-10.5_
  - _Design: §5.1 (ventana_horas bug fix)_


- [x] 1.16 [GREEN] Fix [BUG-001] ventana_horas in calculations/windows.py
  - **Do**:
    1. Create `calculations/windows.py` with `calculate_charging_window_pure`, `calculate_multi_trip_charging_windows`
    2. Fix line ~698: change `trip_arrival_aware - window_start_aware` to `trip_departure_aware - window_start_aware` in delta computation
    3. Leave `trip_arrival` variable (needed for `previous_arrival` downstream)
    4. Update `calculations/__init__.py` to re-export from `.windows`
  - **Files**: custom_components/ev_trip_planner/calculations/windows.py, calculations/__init__.py, calculations.py
  - **Done when**: Test from 1.15 passes; window functions importable from `calculations.windows`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_ventana_horas_invariant.py -v && echo GREEN_PASS`
  - **Commit**: `fix(spec3): [BUG-001] ventana_horas uses trip_departure not trip_arrival`
  - _Requirements: AC-10.1, AC-10.4_
  - _Design: §5.1 (ventana_horas bug fix)_

- [x] 1.17 [RED] Test: [BUG-002] previous_arrival has no redundant return_buffer_hours
  - **Do**: Write test asserting `previous_arrival` in multi-trip calculation equals `previous_trip.departure_time + duration_hours` (NOT `+ return_buffer_hours`)
  - **Files**: tests/unit/test_previous_arrival_invariant.py
  - **Done when**: Test exists and fails (current code adds `+ return_buffer_hours`)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_previous_arrival_invariant.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - [BUG-002] previous_arrival must not double-count return_buffer_hours`
  - _Requirements: AC-10.2, AC-13.1, AC-13.3_
  - _Design: §5.1 (previous_arrival bug fix)_


- [x] 1.18 [GREEN] Fix [BUG-002] previous_arrival in calculations/windows.py
  - **Do**:
    1. In `calculate_multi_trip_charging_windows`, replace `previous_arrival = trip_arrival + timedelta(hours=return_buffer_hours)` with `window_start = previous_departure + timedelta(hours=return_buffer_hours)`
    2. Window start now correctly uses `previous_departure` instead of `trip_arrival`
  - **Files**: custom_components/ev_trip_planner/calculations/windows.py
  - **Done when**: Both bug fix tests (1.15, 1.17) pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_ventana_horas_invariant.py tests/unit/test_previous_arrival_invariant.py -v && echo GREEN_PASS`
  - **Commit**: `fix(spec3): [BUG-002] remove redundant return_buffer_hours from previous_arrival`
  - _Requirements: AC-10.2, AC-10.4, AC-13.1, AC-13.3_
  - _Design: §5.1 (previous_arrival bug fix)_

- [x] 1.19 [YELLOW] Update hora_regreso test assertions to corrected values
  - **Do**:
    1. In `tests/unit/test_single_trip_hora_regreso_past.py`, update assertions:
       - Line 57: 102.0 -> 96.0 (correct: departure - start, not arrival - start)
       - Line 97: 102.0 -> 96.0
       - Line 128: 98.0 -> 92.0
    2. Update inline rationale comments ("should be ~102h" -> "should be ~96h"; "should be 98h" -> "should be 92h")
    3. Also update `tests/unit/test_charging_window.py` tests that used `trip_arrival` as window start for subsequent trips
  - **Files**: tests/unit/test_single_trip_hora_regreso_past.py, tests/unit/test_charging_window.py
  - **Done when**: All assertions match corrected formula values
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_single_trip_hora_regreso_past.py tests/unit/test_charging_window.py -v && echo YELLOW_PASS`
  - **Commit**: `fix(spec3): update test assertions for [BUG-001] corrected values`
  - _Requirements: AC-10.3_
  - _Design: §5.1 (hora_regreso test assertions)_

- [ ] V1b [VERIFY] Quality check: calculations bug fixes pass (BUG-001 + BUG-002) + full suite
  - **Do**:
    1. Run lint + typecheck
    2. Run invariant tests: `test_ventana_horas_invariant.py` and `test_previous_arrival_invariant.py`
    3. Run AC-10.3 hardcoded-value regression: `test_single_trip_hora_regreso_past.py`
    4. **RUN FULL SUITE**: `make test-cover` — ALL tests must pass (NO pre-existing excuse)
    5. **Pattern verification**: Verify `calculations/windows.py` uses pure functions (no class), `calculations/core.py` re-exports via `__all__` pattern
    6. **New-file coverage**: Verify that newly created files (`calculations/windows.py`, `calculations/power.py`, `calculations/schedule.py`, `calculations/core.py`) have coverage in `make test-cover` output — legacy shim files excluded
  - **Verify**: `make lint && make typecheck && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_ventana_horas_invariant.py tests/unit/test_previous_arrival_invariant.py tests/unit/test_single_trip_hora_regreso_past.py -v && make test-cover 2>&1 | grep -q "passed, 0 failed" && echo VF_BUG_PASS`
  - **Done when**: All bug-fix tests pass; full suite shows 0 failures; new modules follow design patterns; newly created files have coverage (legacy shims excluded from coverage gate)
  - **Commit**: `chore(spec3): pass quality checkpoint calculations/bug-fixes [BUG-001][BUG-002] + full-suite`
  - _Requirements: NFR-7.A, AC-10.1, AC-10.2, AC-10.3, AC-13.1, AC-13.3_
  - _Design: §7 + §5.1 (calculations bug fix validation)_
  - **Rule**: "pre-existing failure" is NOT a valid excuse. If a test fails after bug-fix, it must be fixed or moved to `tests_excluded_from_mutmut/`

- [x] 1.20 [RED] Test: power.py re-exports `calculate_power_profile_from_trips` and `calculate_power_profile`
  - **Do**: Write test importing both functions from `calculations.power`
  - **Files**: tests/unit/test_calculations_power.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_power.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - calculations.power must export power profile functions`
  - _Requirements: AC-2.4_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.21 [GREEN] Move power profile functions to `power.py`
  - **Do**:
    1. Extract `calculate_power_profile_from_trips` (~209 LOC) and `calculate_power_profile` (~144 LOC) to `calculations/power.py`
    2. Update `calculations/__init__.py` to re-export from `.power`
    3. Update `calculations.py` shim to import from `.power`
  - **Files**: custom_components/ev_trip_planner/calculations/power.py, calculations/__init__.py, calculations.py
  - **Done when**: Functions importable from `calculations.power`; all calculations tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_power.py tests/unit/test_calculations.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move power profile functions to calculations/power.py`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_


- [x] 1.22 [RED] Test: schedule.py re-exports schedule functions
  - **Do**: Write test importing `generate_deferrable_schedule_from_trips` and `calculate_deferrable_parameters` from `calculations.schedule`
  - **Files**: tests/unit/test_calculations_schedule.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_schedule.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - calculations.schedule must export schedule functions`
  - _Requirements: AC-2.4_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.23 [GREEN] Move schedule functions to `schedule.py`
  - **Do**:
    1. Extract `generate_deferrable_schedule_from_trips` and `calculate_deferrable_parameters` to `calculations/schedule.py`
    2. Update `calculations/__init__.py` to re-export from `.schedule`
    3. Update `calculations.py` shim
  - **Files**: custom_components/ev_trip_planner/calculations/schedule.py, calculations/__init__.py, calculations.py
  - **Done when**: Functions importable from `calculations.schedule`; all calculations tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_schedule.py tests/unit/test_deferrables_schedule.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move schedule functions to calculations/schedule.py`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_


- [x] 1.24 [RED] Test: deficit.py re-exports deficit/scheduling functions
  - **Do**: Write test importing `calculate_deficit_propagation`, `calculate_next_recurring_datetime`, `determine_charging_need`, `ChargingDecision`, `calculate_energy_needed` from `calculations.deficit`
  - **Files**: tests/unit/test_calculations_deficit.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_deficit.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - calculations.deficit must export deficit functions`
  - _Requirements: AC-2.4_
  - _Design: §3.6 (calculations functional decomposition)_

- [x] 1.25 [GREEN] Move deficit functions to `deficit.py`
  - **Do**:
    1. Extract `calculate_deficit_propagation`, `calculate_next_recurring_datetime`, `determine_charging_need`, `ChargingDecision`, `calculate_energy_needed` to `calculations/deficit.py`
    2. Update `calculations/__init__.py` to re-export from `.deficit`
    3. Update `calculations.py` shim
  - **Files**: custom_components/ev_trip_planner/calculations/deficit.py, calculations/__init__.py, calculations.py
  - **Done when**: All 5 names importable from `calculations.deficit`; all calculations tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_deficit.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move deficit functions to calculations/deficit.py`
  - _Requirements: FR-1.1_
  - _Design: §3.6 (calculations functional decomposition)_


- [x] 1.26 [YELLOW] Remove transitional calculations.py shim
  - **Do**:
    1. Remove `calculations.py` shim file
    2. Update all internal imports (`emhass_adapter.py`, `trip_manager.py`) to import from `custom_components.ev_trip_planner.calculations`
    3. Verify `make test` passes
  - **Files**: custom_components/ev_trip_planner/calculations.py (delete), emhass_adapter.py, trip_manager.py
  - **Done when**: No `calculations.py` file exists; all imports resolve to package
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_calculations_imports.py tests/unit/test_charging_window.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove calculations.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: §3.6 + §4.6 (transitional shim removal)_

- [x] 1.27 [VERIFY] Update mutation config for calculations modules
  - **Do**:
    1. Remove `[tool.quality-gate.mutation.modules.calculations]` from pyproject.toml
    2. Add entries for `calculations.core`, `calculations.windows`, `calculations.power`, `calculations.schedule`, `calculations.deficit` inheriting original `kill_threshold`
  - **Files**: pyproject.toml
  - **Done when**: Mutation config references only new sub-module paths
  - **Verify**: `grep -A2 'calculations.core\|calculations.windows\|calculations.power\|calculations.schedule\|calculations.deficit' pyproject.toml | grep -q 'kill_threshold' && echo VERIFY_PASS`
  - **Commit**: `chore(spec3): update mutation config for calculations sub-modules`
  - _Requirements: FR-5.1_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [x] V2 [VERIFY] Quality check: ruff check && pyright && make test-cover (0 failures, pattern verification)
  - **Do**: Run quality checks after calculations decomposition
  - **Verify**: `make lint && make typecheck && make test-cover 2>&1 | grep -q "passed, 0 failed" && echo VERIFY_PASS`
  - **Done when**: No lint errors, no type errors, full test suite shows 0 failures; new files (`calculations/`) have coverage; pattern check: pure functions + `__all__` exports
  - **Commit**: `chore(spec3): pass quality checkpoint calculations`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, calculations)_
  - **Rule**: "pre-existing failure" is NOT a valid excuse. Legacy shim files excluded from coverage gate during active migration.

### 1.2 vehicle/ - Strategy Pattern (mostly file extraction)

- [ ] 1.28 [RED] Test: vehicle package re-exports VehicleController, VehicleControlStrategy, create_control_strategy
  - **Do**: Write test importing all 3 public names from `custom_components.ev_trip_planner.vehicle`
  - **Files**: tests/unit/test_vehicle_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - vehicle package must re-export 3 public names`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.5 (vehicle Strategy pattern)_

- [x] 1.29 [GREEN] Scaffold vehicle/ with re-exports and shims
  - **Do**:
    1. Create `custom_components/ev_trip_planner/vehicle/` directory
    2. Create `__init__.py` re-exporting 3 names from sub-modules
    3. Create stub sub-modules: `strategy.py`, `external.py`, `controller.py`
    4. Keep `vehicle_controller.py` as transitional shim re-exporting from `vehicle/`
  - **Files**: custom_components/ev_trip_planner/vehicle/__init__.py, vehicle/*.py, vehicle_controller.py (shim)
  - **Done when**: 3 public names importable from `vehicle/`; existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_imports.py tests/unit/test_vehicle_controller.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold vehicle/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.5 (vehicle Strategy pattern)_

- [x] 1.30 [RED] Test: VehicleControlStrategy ABC is importable from vehicle.strategy
  - **Do**: Write test importing `VehicleControlStrategy` ABC from `vehicle.strategy` and asserting it has 3 abstract methods
  - **Files**: tests/unit/test_vehicle_strategy.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_strategy.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - VehicleControlStrategy ABC must be in vehicle.strategy`
  - _Requirements: FR-1.4_
  - _Design: §3.5 (vehicle Strategy pattern)_



- [x] 1.31 [GREEN] Move ABC and strategies to `strategy.py`
  - **Do**:
    1. Move `VehicleControlStrategy` ABC (3 abstract methods: `async_activate`, `async_deactivate`, `async_get_status`), `SwitchStrategy`, `ServiceStrategy`, `RetryState`, `HomeAssistantWrapper` from `vehicle_controller.py` to `vehicle/strategy.py`
  - **Files**: custom_components/ev_trip_planner/vehicle/strategy.py, vehicle_controller.py
  - **Done when**: ABC importable from `vehicle.strategy`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_strategy.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move ABC and strategies to vehicle/strategy.py`
  - _Requirements: FR-1.4_
  - _Design: §3.5 (vehicle Strategy pattern)_

- [x] 1.32 [RED] Test: ScriptStrategy and ExternalStrategy importable from vehicle.external
  - **Do**: Write test importing `ScriptStrategy` and `ExternalStrategy` from `vehicle.external`
  - **Files**: tests/unit/test_vehicle_external.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_external.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - external strategies must be in vehicle.external`
  - _Requirements: FR-1.1_
  - _Design: §3.5 (vehicle Strategy pattern)_


- [x] 1.33 [GREEN] Move external strategies to `external.py`
  - **Do**:
    1. Move `ScriptStrategy` and `ExternalStrategy` from `vehicle_controller.py` to `vehicle/external.py`
  - **Files**: custom_components/ev_trip_planner/vehicle/external.py, vehicle_controller.py
  - **Done when**: External strategies importable from `vehicle.external`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_external.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move external strategies to vehicle/external.py`
  - _Requirements: FR-1.1_
  - _Design: §3.5 (vehicle Strategy pattern)_

- [x] 1.34 [RED] Test: VehicleController and factory importable from vehicle.controller
  - **Do**: Write test importing `VehicleController` and `create_control_strategy` from `vehicle.controller`
  - **Files**: tests/unit/test_vehicle_controller_impl.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_controller_impl.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - VehicleController must be in vehicle.controller`
  - _Requirements: AC-2.3_
  - _Design: §3.5 (vehicle Strategy pattern)_


- [x] 1.35 [GREEN] Move VehicleController to `controller.py`
  - **Do**:
    1. Move `VehicleController` class and `create_control_strategy` factory from `vehicle_controller.py` to `vehicle/controller.py`
    2. Verify constructor signature unchanged (AC-2.3)
  - **Files**: custom_components/ev_trip_planner/vehicle/controller.py, vehicle_controller.py
  - **Done when**: Class importable from `vehicle.controller`; constructor signature verified; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_controller_impl.py tests/unit/test_vehicle_controller_event.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move VehicleController to vehicle/controller.py`
  - _Requirements: AC-2.3_
  - _Design: §3.5 (vehicle Strategy pattern)_

- [x] 1.36 [YELLOW] Remove vehicle_controller.py shim
  - **Do**:
    1. Delete `vehicle_controller.py`
    2. Update `trip_manager.py` import from `from .vehicle_controller import VehicleController` to `from .vehicle import VehicleController`
    3. Verify `make test` passes
  - **Files**: custom_components/ev_trip_planner/vehicle_controller.py (delete), trip_manager.py
  - **Done when**: No `vehicle_controller.py` exists; all imports resolve
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_vehicle_controller*.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove vehicle_controller.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: §3.5 + §4.6 (transitional shim removal)_


- [ ] 1.37 [VERIFY] Update mutation config for vehicle modules
  - **Do**:
    1. Remove `[tool.quality-gate.mutation.modules.vehicle_controller]` from pyproject.toml
    2. Add entries for `vehicle.controller`, `vehicle.strategy`, `vehicle.external` inheriting original `kill_threshold`
  - **Files**: pyproject.toml
  - **Done when**: Mutation config references only new sub-module paths
  - **Verify**: `grep -A2 'vehicle.controller\|vehicle.strategy\|vehicle.external' pyproject.toml | grep -q 'kill_threshold' && echo VERIFY_PASS`
  - **Commit**: `chore(spec3): update mutation config for vehicle sub-modules`
  - _Requirements: FR-5.1_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [ ] V3 [VERIFY] Quality check: ruff check && pyright
  - **Do**: Run quality checks after vehicle decomposition
  - **Verify**: `make lint && make typecheck`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint vehicle`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, vehicle)_

### 1.3 dashboard/ - Facade + Builder + `__file__` Path Fix

- [ ] 1.38 [RED] Test: template files exist in dashboard/templates/
  - **Do**: Write test asserting all 11 template files are present in `custom_components/ev_trip_planner/dashboard/templates/`
  - **Files**: tests/unit/test_dashboard_templates.py
  - **Done when**: Test exists and fails (templates not yet moved)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_templates.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - dashboard templates must be in templates/ subdirectory`
  - _Requirements: AC-7.3_
  - _Design: §3.4 + §4.3 (dashboard pathlib pre-condition)_

- [ ] 1.39 [GREEN] Move 11 template files to dashboard/templates/
  - **Do**:
    1. Create `custom_components/ev_trip_planner/dashboard/templates/` directory
    2. Move all 11 YAML/JS template files from `dashboard/` to `dashboard/templates/`
    3. Verify file permissions preserved
  - **Files**: custom_components/ev_trip_planner/dashboard/templates/* (moved)
  - **Done when**: All 11 template files in `dashboard/templates/`; `dashboard/` still only contains templates dir (no `__init__.py` yet)
  - **Verify**: `test -d custom_components/ev_trip_planner/dashboard/templates && ls custom_components/ev_trip_planner/dashboard/templates/ | wc -l | grep -q '^11$' && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move 11 template files to dashboard/templates/`
  - _Requirements: AC-7.3_
  - _Design: §3.4 + §4.3 (dashboard pathlib pre-condition)_

- [ ] 1.40 [RED] Test: dashboard template loading works with new path structure
  - **Do**: Write test calling `import_dashboard` from `dashboard.py` and asserting template files load without FileNotFoundError
  - **Files**: tests/unit/test_dashboard_template_paths.py
  - **Done when**: Test exists and fails (path still uses old `os.path.dirname(__file__) + "dashboard" + template`)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_template_paths.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - dashboard template paths must work after templates move`
  - _Requirements: AC-7.1_
  - _Design: §3.4 + §4.3 (dashboard pathlib pre-condition)_



- [ ] 1.41 [GREEN] Fix template path in dashboard.py for new templates/ subdirectory
  - **Do**:
    1. Update template path resolution in `dashboard.py`: change `os.path.join(comp_dir, "dashboard", template_file)` to `os.path.join(comp_dir, "templates", template_file)`
    2. This is the pre-condition before creating `dashboard/__init__.py` - the old `dashboard.py` file stays, only the path string changes
  - **Files**: custom_components/ev_trip_planner/dashboard.py
  - **Done when**: Template files load from new path; `make e2e-soc` passes
  - **Verify**: `test -f custom_components/ev_trip_planner/dashboard.py && ! test -f custom_components/ev_trip_planner/dashboard/__init__.py && echo GREEN_PASS`
  - **Commit**: `fix(spec3): [BUG-003] fix template path for new dashboard/templates/ structure`
  - _Requirements: AC-7.1, AC-7.2_
  - _Design: §3.4 + §4.3 (dashboard pathlib pre-condition)_

- [ ] 1.42 [RED] Test: dashboard package re-exports public API
  - **Do**: Write test importing `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`, and 4 exception classes from `custom_components.ev_trip_planner.dashboard`
  - **Files**: tests/unit/test_dashboard_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - dashboard package must re-export 7 public names + 4 exceptions`
  - _Requirements: AC-2.4_
  - _Design: §3.4 (dashboard Facade + Builder)_


- [ ] 1.43 [GREEN] Create dashboard/__init__.py with re-exports
  - **Do**:
    1. Create `custom_components/ev_trip_planner/dashboard/__init__.py` with `from __future__ import annotations`
    2. Re-export `import_dashboard`, `is_lovelace_available`, `DashboardImportResult`, and 4 exception classes from `importer.py` and `exceptions.py`
    3. Create `dashboard/exceptions.py` with the 4 exception classes
    4. Create `dashboard/_paths.py` with `TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"` (depth-robust path resolution)
  - **Files**: custom_components/ev_trip_planner/dashboard/__init__.py, dashboard/exceptions.py, dashboard/_paths.py
  - **Done when**: 7 names + exceptions importable from `dashboard/`; `dashboard.py` still exists as transitional authority
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): create dashboard/__init__.py with re-exports and TEMPLATES_DIR`
  - _Requirements: AC-2.4, AC-7.2_
  - _Design: §3.4 + §4.3 (dashboard Facade + TEMPLATES_DIR)_

- [ ] V4 [VERIFY] Quality check: ruff check && pyright
  - **Do**: Run quality checks after initial dashboard package creation
  - **Verify**: `make lint && make typecheck`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint dashboard-init`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, dashboard-init)_

- [ ] 1.44 [RED] Test: template_manager.py functions are importable from dashboard.template_manager
  - **Do**: Write test importing template I/O functions (`load_template`, `save_lovelace_dashboard`, `save_yaml_fallback`, `validate_config`, `verify_storage_permissions`) from `dashboard.template_manager`
  - **Files**: tests/unit/test_dashboard_template_manager.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_template_manager.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - template I/O must be in dashboard.template_manager`
  - _Requirements: FR-1.1_
  - _Design: §3.4 (dashboard Facade + Builder)_

- [ ] 1.45 [GREEN] Move template I/O to `template_manager.py`
  - **Do**:
    1. Extract template loading/saving/validation functions from `dashboard.py` to `dashboard/template_manager.py`
    2. Use `TEMPLATES_DIR` from `_paths.py` instead of `os.path.dirname(__file__)`
    3. Update `dashboard.py` to delegate to `template_manager`
  - **Files**: custom_components/ev_trip_planner/dashboard/template_manager.py, dashboard.py
  - **Done when**: Template functions importable from `dashboard.template_manager`; dashboard tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard.py::TestLoadTemplate -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move template I/O to dashboard/template_manager.py`
  - _Requirements: FR-1.1, AC-7.2_
  - _Design: §3.4 + §4.3 (dashboard Facade + TEMPLATES_DIR)_

- [ ] 1.46 [RED] Test: DashboardBuilder construct dashboard config
  - **Do**: Write test asserting `DashboardBuilder.with_title().add_status_view().add_trip_list_view().build()` produces valid config dict
  - **Files**: tests/unit/test_dashboard_builder.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_builder.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - DashboardBuilder must produce valid config`
  - _Requirements: FR-1.1_
  - _Design: §3.4 (dashboard Builder)_



- [ ] 1.47 [GREEN] Create `DashboardBuilder` in `builder.py`
  - **Do**:
    1. Extract dashboard config construction logic from `import_dashboard` into `DashboardBuilder` class in `dashboard/builder.py`
    2. Keep `import_dashboard` in `dashboard/importer.py` as orchestrator (~80 LOC)
    3. `DashboardBuilder` fluent interface: `with_title()`, `add_status_view()`, `add_trip_list_view()`, `build()`
  - **Files**: custom_components/ev_trip_planner/dashboard/builder.py, dashboard/importer.py, dashboard.py
  - **Done when**: Builder importable from `dashboard.builder`; dashboard tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_builder.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): create DashboardBuilder in dashboard/builder.py`
  - _Requirements: FR-1.1, AC-1.5_
  - _Design: §3.4 (dashboard Builder)_

- [ ] 1.48 [RED] Test: dashboard.py transitional shim re-exports all public + private names
  - **Do**: Write test asserting that `from dashboard import _load_dashboard_template` (and similar private helpers) still resolves through the shim
  - **Files**: tests/unit/test_dashboard_shim.py
  - **Done when**: Test exists and fails (shim not yet created)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard_shim.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - dashboard.py shim must re-export private helpers for tests`
  - _Requirements: AC-2.5_
  - _Design: §3.4 + §4.6 (dashboard shim re-exports)_


- [ ] 1.49 [GREEN] Make dashboard.py transitional shim re-exporting from package
  - **Do**:
    1. Convert `dashboard.py` to 1-line shim re-exporting public names from `dashboard/` package
    2. Re-export ~11 private helpers (`_load_dashboard_template`, etc.) from sub-modules for test compatibility
    3. Each private re-export annotated with `# transitional` comment
  - **Files**: custom_components/ev_trip_planner/dashboard.py
  - **Done when**: All test imports from `dashboard` resolve; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard.py tests/unit/test_dashboard_validation.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): turn dashboard.py into transitional shim re-exporting package`
  - _Requirements: AC-2.5_
  - _Design: §3.4 + §4.6 (dashboard shim re-exports)_

- [ ] 1.50 [YELLOW] Verify dashboard end-to-end: e2e-soc passes
  - **Do**: Run `make e2e-soc` to verify dashboard template loading works end-to-end
  - **Files**: N/A (verification only)
  - **Done when**: `make e2e-soc` passes
  - **Verify**: `make e2e-soc && echo YELLOW_PASS`
  - **Commit**: `chore(spec3): verify dashboard e2e after template path fix`
  - _Requirements: AC-7.1, AC-3.3_
  - _Design: §3.4 + §4.3 (dashboard e2e verification)_


- [ ] 1.51 [YELLOW] Update dashboard.py test imports to use new paths (Phase 2)
  - **Do**:
    1. Update `tests/unit/test_dashboard.py` imports: change `from custom_components.ev_trip_planner.dashboard import _load_dashboard_template` to `from custom_components.ev_trip_planner.dashboard.template_manager import _load_dashboard_template`
    2. Same for all ~80 import sites in `test_dashboard.py` and `test_dashboard_validation.py`
    3. Update both files' imports to point at `dashboard.template_manager` and `dashboard.builder`
  - **Files**: tests/unit/test_dashboard.py, tests/unit/test_dashboard_validation.py
  - **Done when**: All ~80 test imports redirected to sub-module paths; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_dashboard.py tests/unit/test_dashboard_validation.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): update dashboard test imports to use sub-module paths`
  - _Requirements: AC-2.5_
  - _Design: §4.6 (Test Import Migration)_

- [ ] 1.52 [YELLOW] Remove dashboard.py transitional shim
  - **Do**:
    1. Delete `dashboard.py`
    2. Verify `config_flow.py` and `services.py` imports (`from .dashboard import import_dashboard`) still resolve — no edit needed because the new `dashboard/__init__.py` re-exports the same symbol
    3. Verify `make test` and `make e2e-soc` pass
  - **Files**: custom_components/ev_trip_planner/dashboard.py (delete)
  - **Done when**: `dashboard.py` file removed; all imports resolve through package
  - **Verify**: `! test -f custom_components/ev_trip_planner/dashboard.py && PYTHONPATH=. .venv/bin/python -c "from custom_components.ev_trip_planner.dashboard import import_dashboard" && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove dashboard.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: §3.4 + §4.6 (transitional shim removal)_


- [ ] 1.53 [VERIFY] Update mutation config for dashboard modules
  - **Do**:
    1. Remove `[tool.quality-gate.mutation.modules.dashboard]` from pyproject.toml
    2. Add entries for `dashboard.importer`, `dashboard.builder`, `dashboard.template_manager` inheriting original `kill_threshold`
  - **Files**: pyproject.toml
  - **Done when**: Mutation config references only new sub-module paths
  - **Verify**: `grep -A2 'dashboard.importer\|dashboard.builder\|dashboard.template_manager' pyproject.toml | grep -q 'kill_threshold' && echo VERIFY_PASS`
  - **Commit**: `chore(spec3): update mutation config for dashboard sub-modules`
  - _Requirements: FR-5.1_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [ ] V5 [VERIFY] Quality check: ruff check && pyright && make test-cover (0 failures, pattern verification)
  - **Do**: Run quality checks after dashboard decomposition
  - **Verify**: `make lint && make typecheck && make test-cover 2>&1 | grep -q "passed, 0 failed" && echo VERIFY_PASS`
  - **Done when**: No lint errors, no type errors, full test suite shows 0 failures; pattern check: `dashboard/` uses Builder pattern for config construction per design §3.4; new files have coverage
  - **Commit**: `chore(spec3): pass quality checkpoint dashboard`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, dashboard)_
  - **Rule**: "pre-existing failure" is NOT a valid excuse. Pattern check: `dashboard/` uses Builder pattern per design §3.4.

### 1.4 emhass/ - Facade + Composition

- [ ] 1.54 [RED] Test: emhass package re-exports EMHASSAdapter
  - **Do**: Write test importing `EMHASSAdapter` from `custom_components.ev_trip_planner.emhass`
  - **Files**: tests/unit/test_emhass_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - emhass package must re-export EMHASSAdapter`
  - _Requirements: AC-2.4_
  - _Design: §3.1 (emhass Facade + Composition)_

- [ ] 1.55 [GREEN] Scaffold emhass/ with re-exports and shims
  - **Do**:
    1. Create `custom_components/ev_trip_planner/emhass/` directory
    2. Create `__init__.py` re-exporting `EMHASSAdapter` from `adapter.py`
    3. Create stub sub-modules: `adapter.py`, `index_manager.py`, `load_publisher.py`, `error_handler.py`, `_cache_entry_builder.py`
    4. Keep `emhass_adapter.py` as transitional shim
  - **Files**: custom_components/ev_trip_planner/emhass/__init__.py, emhass/*.py, emhass_adapter.py (shim)
    > Justification: scaffold creates a new package alongside a shim — all 5 stub files + __init__.py must land in one commit to keep import surface coherent and `make test` green.
  - **Done when**: `EMHASSAdapter` importable from `emhass/`; 24+ test imports resolve; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold emhass/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.1 (emhass Facade + Composition)_

- [ ] 1.56 [RED] Test: IndexManager class exists in emhass.index_manager
  - **Do**: Write test importing `IndexManager` from `emhass.index_manager` and asserting it has `async_assign`, `async_release`, `get_assigned_index`, `get_all_assigned_indices`, `get_available_indices`, `async_cleanup_vehicle_indices`, `verify_cleanup` methods
  - **Files**: tests/unit/test_emhass_index_manager.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_index_manager.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - IndexManager must be in emhass.index_manager`
  - _Requirements: FR-1.1_
  - _Design: §3.1 (emhass IndexManager)_



- [ ] 1.57 [GREEN] Move index management to `index_manager.py`
  - **Do**:
    1. Extract `IndexManager` class methods (`async_assign_index_to_trip`, `async_release_trip_index`, `get_assigned_index`, `get_all_assigned_indices`, `get_available_indices`, `async_cleanup_vehicle_indices`, `verify_cleanup`, `_get_config_sensor_id`) from `emhass_adapter.py` to `emhass/index_manager.py`
    2. Keep Store persistence, index map, released indices as `IndexManager` state
  - **Files**: custom_components/ev_trip_planner/emhass/index_manager.py, emhass_adapter.py
  - **Done when**: `IndexManager` importable from `emhass.index_manager`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_index_manager.py tests/unit/test_emhass_index_rotation.py tests/unit/test_emhass_index_persistence.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move IndexManager to emhass/index_manager.py`
  - _Requirements: FR-1.1_
  - _Design: §3.1 (emhass IndexManager)_

- [ ] V6 [VERIFY] Quality check: ruff check && pyright after emhass index+load
  - **Do**: Run quality checks after index_manager and load_publisher decomposition
  - **Verify**: `make lint && make typecheck`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint emhass-index`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, emhass-index)_

- [ ] 1.58 [RED] Test: LoadPublisher class exists in emhass.load_publisher
  - **Do**: Write test importing `LoadPublisher` from `emhass.load_publisher` and asserting it has publish/update/remove methods
  - **Files**: tests/unit/test_emhass_load_publisher.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_load_publisher.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - LoadPublisher must be in emhass.load_publisher`
  - _Requirements: FR-1.1_
  - _Design: §3.1 (emhass LoadPublisher)_

- [ ] 1.59 [GREEN] Move load publishing to `load_publisher.py`
  - **Do**:
    1. Extract load publishing methods from `emhass_adapter.py` to `emhass/load_publisher.py`
    2. Extract `_populate_per_trip_cache_entry` (266 LOC) to `emhass/_cache_entry_builder.py` as pure function `build_cache_entry(...)`
    3. `LoadPublisher` owns cache, calls `IndexManager` and `_cache_entry_builder` via DI
  - **Files**: custom_components/ev_trip_planner/emhass/load_publisher.py, emhass/_cache_entry_builder.py, emhass_adapter.py
  - **Done when**: `LoadPublisher` importable from `emhass.load_publisher`; cache entry builder importable; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_deferrable_end.py tests/unit/test_deferrable_start_boundary.py tests/unit/test_deferrable_end_boundary.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move LoadPublisher to emhass/load_publisher.py`
  - _Requirements: FR-1.1, AC-1.6_
  - _Design: §3.1 (emhass LoadPublisher + cache_entry_builder)_

- [ ] 1.60 [RED] Test: ErrorHandler class exists in emhass.error_handler
  - **Do**: Write test importing `ErrorHandler` from `emhass.error_handler` and asserting it has `async_notify_error`, `async_handle_*`, `get_last_error`, `async_clear_error` methods
  - **Files**: tests/unit/test_emhass_error_handler.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_error_handler.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - ErrorHandler must be in emhass.error_handler`
  - _Requirements: FR-1.1_
  - _Design: §3.1 (emhass ErrorHandler)_



- [ ] 1.61 [GREEN] Move error handling to `error_handler.py`
  - **Do**:
    1. Extract error handling methods from `emhass_adapter.py` to `emhass/error_handler.py`
    2. `ErrorHandler` owns `_last_error`, `_notification_service`, `_hass`
    3. Methods: `async_notify_error`, `async_handle_emhass_unavailable`, `async_handle_sensor_error`, `async_handle_shell_command_failure`, `get_last_error`, `async_clear_error`, `async_verify_shell_command_integration`, `async_check_emhass_response_sensors`, `async_get_integration_status`
  - **Files**: custom_components/ev_trip_planner/emhass/error_handler.py, emhass_adapter.py
  - **Done when**: `ErrorHandler` importable from `emhass.error_handler`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_integration_dynamic_soc.py tests/unit/test_emhass_soft_delete.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move ErrorHandler to emhass/error_handler.py`
  - _Requirements: FR-1.1_
  - _Design: §3.1 (emhass ErrorHandler)_

- [ ] 1.62 [RED] Test: EMHASSAdapter facade delegates to sub-components
  - **Do**: Write test that instantiates `EMHASSAdapter` (via shim) and asserts its public methods delegate to sub-component instances (`_index_manager`, `_load_publisher`, `_error_handler`)
  - **Files**: tests/unit/test_emhass_facade.py
  - **Done when**: Test exists and fails (facade not yet wired)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_facade.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - EMHASSAdapter facade must delegate to sub-components`
  - _Requirements: AC-2.1_
  - _Design: §3.1 (emhass Facade delegation)_


- [ ] 1.63 [GREEN] Wire EMHASSAdapter facade in `adapter.py`
  - **Do**:
    1. Create `emhass/adapter.py` with `EMHASSAdapter` as thin facade
    2. `__init__` instantiates `IndexManager`, `LoadPublisher`, `ErrorHandler` via composition
    3. 27 public methods delegate 1-line to sub-component methods
    4. Constructor signature unchanged: `__init__(self, hass, entry)` (AC-2.1)
  - **Files**: custom_components/ev_trip_planner/emhass/adapter.py, emhass/__init__.py, emhass_adapter.py
  - **Done when**: All 27 methods accessible via `EMHASSAdapter`; constructor signature verified; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass_imports.py tests/unit/test_emhass_adapter_trip_id.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): wire EMHASSAdapter facade with composition in emhass/adapter.py`
  - _Requirements: AC-2.1, FR-1.1_
  - _Design: §3.1 (emhass Facade delegation)_

- [ ] 1.64 [YELLOW] Remove emhass_adapter.py shim
  - **Do**:
    1. Delete `emhass_adapter.py`
    2. Update source imports: `__init__.py`, `coordinator.py`, `trip_manager.py` -> `from .emhass import EMHASSAdapter`
    3. Verify `make test` passes with all 24+ test imports
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py (delete), __init__.py, coordinator.py, trip_manager.py
  - **Done when**: No `emhass_adapter.py` exists; all source and test imports resolve
  - **Verify**: `! test -f custom_components/ev_trip_planner/emhass_adapter.py && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_emhass*.py tests/integration/test_emhass*.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove emhass_adapter.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: §3.1 + §4.6 (transitional shim removal)_


- [ ] 1.65 [VERIFY] Update mutation config for emhass modules
  - **Do**:
    1. Remove `[tool.quality-gate.mutation.modules.emhass_adapter]` from pyproject.toml
    2. Add entries for `emhass.adapter`, `emhass.index_manager`, `emhass.load_publisher`, `emhass.error_handler`, `emhass.cache_entry_builder` inheriting original `kill_threshold`
  - **Files**: pyproject.toml
  - **Done when**: Mutation config references only new sub-module paths
  - **Verify**: `grep -A2 'emhass.adapter\|emhass.index_manager\|emhass.load_publisher\|emhass.error_handler' pyproject.toml | grep -q 'kill_threshold' && echo VERIFY_PASS`
  - **Commit**: `chore(spec3): update mutation config for emhass sub-modules`
  - _Requirements: FR-5.1_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [ ] V7 [VERIFY] Quality check: ruff check && pyright && make test-cover (0 failures, pattern verification)
  - **Do**: Run quality checks after emhass decomposition
  - **Verify**: `make lint && make typecheck && make test-cover 2>&1 | grep -q "passed, 0 failed" && echo VERIFY_PASS`
  - **Done when**: No lint errors, no type errors, full test suite shows 0 failures; pattern check: `emhass/` uses Facade + Composition with sub-components (IndexManager, LoadPublisher, ErrorHandler) per design §3.1; new files have coverage
  - **Commit**: `chore(spec3): pass quality checkpoint emhass`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, emhass)_
  - **Rule**: "pre-existing failure" is NOT a valid excuse. Pattern check: `emhass/` uses Facade + Composition per design §3.1.

### 1.5 trip/ - Facade + Mixins + SensorCallbackRegistry

- [ ] 1.66 [RED] Test: trip package re-exports TripManager, CargaVentana, SOCMilestoneResult
  - **Do**: Write test importing `TripManager`, `CargaVentana`, `SOCMilestoneResult` from `custom_components.ev_trip_planner.trip`
  - **Files**: tests/unit/test_trip_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - trip package must re-export 3 public names`
  - _Requirements: AC-2.4_
  - _Design: §3.2 (trip Facade + Mixins)_

- [ ] 1.67 [GREEN] Scaffold trip/ with re-exports and shims
  - **Do**:
    1. Create `custom_components/ev_trip_planner/trip/` directory
    2. Create `__init__.py` re-exporting `TripManager`, `CargaVentana`, `SOCMilestoneResult`
    3. Create stub sub-modules: `manager.py`, `_crud_mixin.py`, `_soc_mixin.py`, `_power_profile_mixin.py`, `_schedule_mixin.py`, `_sensor_callbacks.py`, `_types.py`
    4. Keep `trip_manager.py` as transitional shim
  - **Files**: custom_components/ev_trip_planner/trip/__init__.py, trip/*.py, trip_manager.py (shim)
    > Justification: scaffold creates a new package with mixins — all 7 stub files (manager + 5 mixins + _types) + __init__.py must land in one commit to keep mixin-based facade importable and `make test` green.
  - **Done when**: 3 public names importable from `trip/`; existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold trip/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.2 (trip Facade + Mixins)_

- [ ] 1.68 [RED] Test: SensorCallbackRegistry class exists and works
  - **Do**: Write test importing `SensorCallbackRegistry` from `trip._sensor_callbacks`, asserting `register(event, cb)` and `await emit(event, *args)` work correctly, and missing callback emits WARNING
  - **Files**: tests/unit/test_sensor_callback_registry.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_sensor_callback_registry.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - SensorCallbackRegistry must replace 7 lazy sensor imports`
  - _Requirements: AC-8.1, AC-8.5_
  - _Design: §4.2 (SensorCallbackRegistry)_



- [ ] 1.69 [GREEN] Create SensorCallbackRegistry in `_sensor_callbacks.py`
  - **Do**:
    1. Create `trip/_sensor_callbacks.py` with `SensorCallbackRegistry` class
    2. Exposes `register(event, cb)` and `await emit(event, *args, **kwargs)`
    3. Missing callback: logs WARNING + no-op (per design §4.2)
    4. Define `SensorCallbackProtocol` typed callable signatures
  - **Files**: custom_components/ev_trip_planner/trip/_sensor_callbacks.py
  - **Done when**: `SensorCallbackRegistry` importable and functional; test passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_sensor_callback_registry.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): add SensorCallbackRegistry to replace lazy sensor imports`
  - _Requirements: AC-8.1, AC-8.5_
  - _Design: §4.2 (SensorCallbackRegistry)_

- [ ] 1.70 [RED] Test: _types.py TypedDicts exist and are importable
  - **Do**: Write test importing `CargaVentana` and `SOCMilestoneResult` TypedDicts from `trip._types`
  - **Files**: tests/unit/test_trip_types.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_types.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - TypedDicts must be in trip._types`
  - _Requirements: FR-1.1_
  - _Design: §3.2 (trip TypedDicts)_


- [ ] 1.71 [GREEN] Extract TypedDicts to `_types.py`
  - **Do**:
    1. Move `CargaVentana` and `SOCMilestoneResult` TypedDict definitions from `trip_manager.py` to `trip/_types.py`
    2. Update `trip/__init__.py` to re-export from `.types`
  - **Files**: custom_components/ev_trip_planner/trip/_types.py, trip/__init__.py, trip_manager.py
  - **Done when**: TypedDicts importable from `trip._types`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_types.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): extract TypedDicts to trip/_types.py`
  - _Requirements: FR-1.1_
  - _Design: §3.2 (trip TypedDicts)_

- [ ] 1.72 [RED] Test: _CRUDMixin class has CRUD operations
  - **Do**: Write test asserting `_CRUDMixin` has methods: `async_setup`, `async_add_recurring_trip`, `async_update_trip`, `async_delete_trip`, `async_pause_recurring_trip`, `async_resume_recurring_trip`, `async_complete_punctual_trip`, `async_cancel_punctual_trip`
  - **Files**: tests/unit/test_trip_crud_mixin.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_crud_mixin.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - _CRUDMixin must have CRUD operations`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (CRUD mixin)_


- [ ] 1.73 [GREEN] Move CRUD methods to `_crud_mixin.py`
  - **Do**:
    1. Move trip lifecycle CRUD methods from `trip_manager.py` to `trip/_crud_mixin.py`
    2. Replace 7 lazy `from .sensor import ...` calls with `self._sensor_callbacks.emit(event, ...)`
    3. Replace lazy `_async_sync_trip_to_emhass` / `_async_publish_new_trip_to_emhass` to use injected `self._emhass_adapter`
    4. Mixin `__init__` uses explicit `_CRUDMixin.__init__(self)` (per design §4.1)
    5. Reads shared state from `self` (`_trips`, `_storage`, `_sensor_callbacks`, `_emhass_adapter`)
  - **Files**: custom_components/ev_trip_planner/trip/_crud_mixin.py, trip_manager.py
  - **Done when**: `_CRUDMixin` importable; 7 lazy imports eliminated; CRUD methods functional
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_crud_mixin.py tests/unit/test_trip_crud.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move CRUD methods to trip/_crud_mixin.py`
  - _Requirements: AC-8.1, AC-8.2, FR-1.1_
  - _Design: §3.2 + §4.1 + §4.2 (CRUD mixin + SensorCallbackRegistry)_


- [ ] 1.74 [RED] Test: _SOCMixin has SOC calculation methods
  - **Do**: Write test importing `_SOCMixin` and asserting it has `async_get_vehicle_soc`, `async_get_kwh_needed_today`, `async_get_hours_needed_today`, `calcular_ventana_carga`, `calcular_ventana_carga_multitrip`, `calcular_soc_inicio_trips`, `calcular_hitos_soc`
  - **Files**: tests/unit/test_trip_soc_mixin.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_soc_mixin.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - _SOCMixin must have SOC calculation methods`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (SOC mixin)_

- [ ] 1.75 [GREEN] Move SOC methods to `_soc_mixin.py`
  - **Do**:
    1. Move SOC calculation methods from `trip_manager.py` to `trip/_soc_mixin.py`
    2. Mixin `__init__` uses explicit `_SOCMixin.__init__(self)`
    3. Reads `_trips`, `hass`, `vehicle_id` from shared `self`
  - **Files**: custom_components/ev_trip_planner/trip/_soc_mixin.py, trip_manager.py
  - **Done when**: `_SOCMixin` importable; SOC tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_soc_mixin.py tests/unit/test_soc_milestone.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move SOC methods to trip/_soc_mixin.py`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (SOC mixin)_

- [ ] 1.76 [RED] Test: _PowerProfileMixin has power profile generation
  - **Do**: Write test importing `_PowerProfileMixin` and asserting `async_generate_power_profile` works
  - **Files**: tests/unit/test_trip_power_profile_mixin.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_power_profile_mixin.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - _PowerProfileMixin must have power profile generation`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (PowerProfile mixin)_



- [ ] 1.77 [GREEN] Move power profile method to `_power_profile_mixin.py`
  - **Do**:
    1. Move `async_generate_power_profile` and helpers from `trip_manager.py` to `trip/_power_profile_mixin.py`
    2. Mixin `__init__` uses explicit `_PowerProfileMixin.__init__(self)`
    3. Reads `_trips`, `hass` from shared `self`
  - **Files**: custom_components/ev_trip_planner/trip/_power_profile_mixin.py, trip_manager.py
  - **Done when**: Mixin importable; power profile tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_power_profile_mixin.py tests/unit/test_power_profile_positions.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move power profile method to trip/_power_profile_mixin.py`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (PowerProfile mixin)_

- [ ] 1.78 [RED] Test: _ScheduleMixin has schedule generation
  - **Do**: Write test importing `_ScheduleMixin` and asserting `async_generate_deferrables_schedule` and `publish_deferrable_loads` work
  - **Files**: tests/unit/test_trip_schedule_mixin.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_schedule_mixin.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - _ScheduleMixin must have schedule generation`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (Schedule mixin)_


- [ ] 1.79 [GREEN] Move schedule methods to `_schedule_mixin.py`
  - **Do**:
    1. Move `async_generate_deferrables_schedule` and `publish_deferrable_loads` from `trip_manager.py` to `trip/_schedule_mixin.py`
    2. Mixin `__init__` uses explicit `_ScheduleMixin.__init__(self)`
    3. Reads `_trips`, `_emhass_adapter` from shared `self`
  - **Files**: custom_components/ev_trip_planner/trip/_schedule_mixin.py, trip_manager.py
  - **Done when**: Mixin importable; schedule tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_schedule_mixin.py tests/unit/test_deferrables_schedule.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move schedule methods to trip/_schedule_mixin.py`
  - _Requirements: FR-1.1_
  - _Design: §3.2 + §4.1 (Schedule mixin)_

- [ ] 1.80 [RED] Test: TripManager facade class delegates to mixins
  - **Do**: Write test asserting `TripManager` is composed of `_CRUDMixin`, `_SOCMixin`, `_PowerProfileMixin`, `_ScheduleMixin` and has `set_emhass_adapter`/`get_emhass_adapter`
  - **Files**: tests/unit/test_trip_facade.py
  - **Done when**: Test exists and fails (facade not yet wired)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_facade.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - TripManager facade must delegate to mixins`
  - _Requirements: AC-2.2_
  - _Design: §3.2 + §4.1 (TripManager facade)_


- [ ] 1.81 [GREEN] Wire TripManager facade in `manager.py`
  - **Do**:
    1. Create `trip/manager.py` with `TripManager(_CRUDMixin, _SOCMixin, _PowerProfileMixin, _ScheduleMixin)`
    2. `__init__` establishes shared state on `self` FIRST, then calls explicit `_Mixin.__init__(self)` for each mixin (per design §4.1)
    3. Instantiates `SensorCallbackRegistry()` in `__init__`
    4. Constructor signature unchanged: `__init__(self, hass, vehicle_id, entry_id, presence_config, storage, emhass_adapter=None)` (AC-2.2)
  - **Files**: custom_components/ev_trip_planner/trip/manager.py, trip/__init__.py, trip_manager.py
  - **Done when**: `TripManager` importable from `trip/`; constructor signature verified; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_facade.py tests/unit/test_trip_manager_core.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): wire TripManager facade with mixins in trip/manager.py`
  - _Requirements: AC-2.2_
  - _Design: §3.2 + §4.1 (TripManager facade mixin chain)_

- [ ] 1.82 [YELLOW] Update trip test imports to new paths (Phase 2)
  - **Do**:
    1. Update test files importing private names from `trip_manager.py` to import from `trip/` sub-modules
    2. Files: `tests/unit/conftest.py` (3 imports), `tests/integration/conftest.py` (2 imports), plus any integration tests
  - **Files**: tests/unit/conftest.py, tests/integration/conftest.py, tests/unit/*.py, tests/integration/*.py
  - **Done when**: All test imports resolved; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_trip_crud.py tests/integration/test_trip_manager_core.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): update trip test imports to use sub-module paths`
  - _Requirements: AC-2.5_
  - _Design: §4.6 (Test Import Migration)_


- [ ] 1.83 [YELLOW] Remove trip_manager.py transitional shim
  - **Do**:
    1. Delete `trip_manager.py`
    2. Update source imports: `__init__.py`, `coordinator.py`, `services.py`, `presence_monitor.py` -> `from .trip import TripManager`
    3. Update `vehicle_controller.py` TYPE_CHECKING import
    4. Verify `make test` passes
  - **Files**: custom_components/ev_trip_planner/trip_manager.py (delete), __init__.py, coordinator.py, services.py, presence_monitor.py, vehicle_controller.py
    > Justification: atomic shim removal — all 5 consumers updated in one commit to avoid transient import errors during decomposition (any in-flight import via the deleted shim would break the module load).
  - **Done when**: No `trip_manager.py` exists; all source imports resolve through package
  - **Verify**: `! test -f custom_components/ev_trip_planner/trip_manager.py && PYTHONPATH=. .venv/bin/python -c "from custom_components.ev_trip_planner.trip import TripManager" && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove trip_manager.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: §3.2 + §4.6 (transitional shim removal)_

- [ ] 1.84 [VERIFY] Update mutation config for trip modules
  - **Do**:
    1. Remove `[tool.quality-gate.mutation.modules.trip_manager]` from pyproject.toml
    2. Add entries for `trip.manager`, `trip.crud_mixin`, `trip.soc_mixin`, `trip.power_profile_mixin`, `trip.schedule_mixin` inheriting original `kill_threshold`
  - **Files**: pyproject.toml
  - **Done when**: Mutation config references only new sub-module paths
  - **Verify**: `grep -A2 'trip.manager\|trip.crud_mixin\|trip.soc_mixin' pyproject.toml | grep -q 'kill_threshold' && echo VERIFY_PASS`
  - **Commit**: `chore(spec3): update mutation config for trip sub-modules`
  - _Requirements: FR-5.1_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [ ] V8 [VERIFY] Quality check: ruff check && pyright && make test-cover (0 failures, pattern verification)
  - **Do**: Run quality checks after trip decomposition
  - **Verify**: `make lint && make typecheck && make test-cover 2>&1 | grep -q "passed, 0 failed" && echo VERIFY_PASS`
  - **Done when**: No lint errors, no type errors, full test suite shows 0 failures; pattern check: `trip/` uses Facade + Mixins (CRUDMixin, SOCMixin, PowerProfileMixin, ScheduleMixin) per design §3.2; new files have coverage
  - **Commit**: `chore(spec3): pass quality checkpoint trip`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, trip)_
  - **Rule**: "pre-existing failure" is NOT a valid excuse. Pattern check: `trip/` uses Facade + Mixins per design §3.2.

### 1.6 services/ - Module Facade + Handler Factory Extraction

- [ ] 1.85 [RED] Test: services package re-exports 10 public functions
  - **Do**: Write test importing all 10 public functions from `custom_components.ev_trip_planner.services`
  - **Files**: tests/unit/test_services_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - services package must re-export 10 public functions`
  - _Requirements: AC-2.4_
  - _Design: §3.3 (services Module-Level Facade)_

- [ ] 1.86 [GREEN] Scaffold services/ with re-exports and shims
  - **Do**:
    1. Create `custom_components/ev_trip_planner/services/` directory
    2. Create `__init__.py` re-exporting 10 public functions from sub-modules
    3. Create stub sub-modules: `handlers.py`, `_handler_factories.py`, `cleanup.py`, `dashboard_helpers.py`, `presence.py`, `_lookup.py`
    4. Keep `services.py` as transitional shim
  - **Files**: custom_components/ev_trip_planner/services/__init__.py, services/*.py, services.py (shim)
  - **Done when**: 10 functions importable from `services/`; existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold services/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §3.3 (services Module-Level Facade)_

- [ ] 1.87 [RED] Test: _handler_factories.py creates handler closures
  - **Do**: Write test asserting `make_*_handler(hass, entry)` functions return async handler functions
  - **Files**: tests/unit/test_services_handler_factories.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_handler_factories.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - handler factories must produce callable closures`
  - _Requirements: FR-1.1, AC-1.5_
  - _Design: §3.3 (services handler factories)_



- [ ] 1.88 [GREEN] Extract handler factories from `register_services`
  - **Do**:
    1. Extract each inner `async def handle_*` from `register_services` into `make_*_handler(hass, entry)` factory functions in `services/_handler_factories.py`
    2. Each factory <= 80 LOC (from 688 LOC total)
    3. Shrink `register_services` to ~80 LOC of `async_register` calls in `services/handlers.py`
  - **Files**: custom_components/ev_trip_planner/services/_handler_factories.py, services/handlers.py, services.py
  - **Done when**: Handler factories importable; `register_services` <= 100 LOC; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_handler_factories.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): extract handler factories from register_services`
  - _Requirements: AC-1.5, AC-6.1_
  - _Design: §3.3 (services handler factories)_

- [ ] 1.89 [RED] Test: cleanup.py functions are importable
  - **Do**: Write test importing `async_cleanup_stale_storage`, `async_cleanup_orphaned_emhass_sensors`, `async_unload_entry_cleanup`, `async_remove_entry_cleanup` from `services.cleanup`
  - **Files**: tests/unit/test_services_cleanup.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_cleanup.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - cleanup functions must be in services.cleanup`
  - _Requirements: FR-1.1_
  - _Design: §3.3 (services cleanup)_


- [ ] 1.90 [GREEN] Move cleanup functions to `cleanup.py`
  - **Do**:
    1. Extract cleanup functions from `services.py` to `services/cleanup.py`
    2. Functions: `async_cleanup_stale_storage`, `async_cleanup_orphaned_emhass_sensors`, `async_unload_entry_cleanup`, `async_remove_entry_cleanup`
  - **Files**: custom_components/ev_trip_planner/services/cleanup.py, services.py
  - **Done when**: Functions importable from `services.cleanup`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_cleanup.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move cleanup functions to services/cleanup.py`
  - _Requirements: FR-1.1_
  - _Design: §3.3 (services cleanup)_

- [ ] 1.91 [RED] Test: dashboard_helpers.py functions are importable
  - **Do**: Write test importing `create_dashboard_input_helpers`, `async_register_panel_for_entry`, `async_register_static_paths`, `async_import_dashboard_for_entry` from `services.dashboard_helpers`
  - **Files**: tests/unit/test_services_dashboard_helpers.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_dashboard_helpers.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - dashboard helpers must be in services.dashboard_helpers`
  - _Requirements: FR-1.1_
  - _Design: §3.3 (services dashboard helpers)_


- [ ] 1.92 [GREEN] Move dashboard helpers to `dashboard_helpers.py`
  - **Do**:
    1. Extract dashboard helper functions from `services.py` to `services/dashboard_helpers.py`
    2. Update `services/__init__.py` to re-export from `.dashboard_helpers`
    3. Update `services.py` shim
  - **Files**: custom_components/ev_trip_planner/services/dashboard_helpers.py, services/__init__.py, services.py
  - **Done when**: Functions importable from `services.dashboard_helpers`; tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_services_dashboard_helpers.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): move dashboard helpers to services/dashboard_helpers.py`
  - _Requirements: FR-1.1_
  - _Design: §3.3 (services dashboard helpers)_

- [ ] 1.93 [YELLOW] Remove services.py transitional shim
  - **Do**:
    1. Delete `services.py`
    2. Update source imports: `__init__.py`, `config_flow.py` -> `from .services import ...`
    3. Verify `make test` passes
  - **Files**: custom_components/ev_trip_planner/services.py (delete), __init__.py, config_flow.py
  - **Done when**: No `services.py` exists; all imports resolve through package
  - **Verify**: `! test -f custom_components/ev_trip_planner/services.py && PYTHONPATH=. .venv/bin/python -c "from custom_components.ev_trip_planner.services import register_services" && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove services.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: §3.3 + §4.6 (transitional shim removal)_


- [ ] 1.94 [VERIFY] Update mutation config for services modules
  - **Do**:
    1. Remove `[tool.quality-gate.mutation.modules.services]` from pyproject.toml
    2. Add entries for `services.handlers`, `services.handler_factories`, `services.cleanup`, `services.dashboard_helpers` inheriting original `kill_threshold`
  - **Files**: pyproject.toml
  - **Done when**: Mutation config references only new sub-module paths
  - **Verify**: `grep -A2 'services.handlers\|services.handler_factories\|services.cleanup\|services.dashboard_helpers' pyproject.toml | grep -q 'kill_threshold' && echo VERIFY_PASS`
  - **Commit**: `chore(spec3): update mutation config for services sub-modules`
  - _Requirements: FR-5.1_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [ ] V9 [VERIFY] Quality check: ruff check && pyright && make test-cover (0 failures, pattern verification)
  - **Do**: Run quality checks after services decomposition
  - **Verify**: `make lint && make typecheck && make test-cover 2>&1 | grep -q "passed, 0 failed" && echo VERIFY_PASS`
  - **Done when**: No lint errors, no type errors, full test suite shows 0 failures; pattern check: `services/` uses module-level dispatcher with `make_*_handler` factory functions per design §3.3; new files have coverage
  - **Commit**: `chore(spec3): pass quality checkpoint services`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, services)_
  - **Rule**: "pre-existing failure" is NOT a valid excuse. Pattern check: `services/` uses factory pattern per design §3.3.

### 1.7 sensor.py - Decomposition + Pyright Error Fixes

- [ ] 1.95 [RED] Test: sensor package re-exports HA platform entities
  - **Do**: Write test importing `async_setup_entry`, `TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripSensor`, `TripEmhassSensor` from `custom_components.ev_trip_planner.sensor`
  - **Files**: tests/unit/test_sensor_imports.py
  - **Done when**: Test exists and fails (package doesn't exist yet)
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_sensor_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - sensor package must re-export HA platform entities`
  - _Requirements: AC-2.4_
  - _Design: design-by-convention (sensor decomp; design.md §3 has no sensor section); NFR-7.A.5 + FR-1.7_

- [ ] 1.96 [GREEN] Scaffold sensor/ with re-exports
  - **Do**:
    1. Create `custom_components/ev_trip_planner/sensor/` directory
    2. Create `__init__.py` re-exporting `async_setup_entry`, 4 Entity classes
    3. Split sensor entities into separate files by entity type
    4. Keep `sensor.py` as transitional shim
  - **Files**: custom_components/ev_trip_planner/sensor/__init__.py, sensor/*.py, sensor.py (shim)
  - **Done when**: All names importable; `make test` passes
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_sensor_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold sensor/ package with re-exports`
  - _Requirements: AC-2.4_
  - _Design: design-by-convention (sensor decomp; design.md §3 has no sensor section); NFR-7.A.5 + FR-1.7_

- [ ] 1.97 [RED] Test: sensor.py has zero pyright errors
  - **Do**: Write a shell-test asserting `make typecheck` reports zero errors for sensor files
  - **Files**: tests/unit/test_sensor_pyright.py
  - **Done when**: Test exists and fails (16 pre-existing pyright errors in sensor.py)
  - **Verify**: `make typecheck 2>&1 | grep -q "Found.*error" && echo RED_PASS`
  - **Commit**: `test(spec3): red - sensor.py must have zero pyright errors`
  - _Requirements: NFR-7.A.5, FR-1.7_
  - _Design: design-by-convention (sensor pyright); NFR-7.A.5 + FR-1.7_



- [ ] 1.98 [GREEN] Fix 16 pyright errors in sensor.py entity classes
  - **Do**:
    1. Fix type annotations in sensor entity classes to match HA `Entity` ABC contract
    2. Fix `async_setup_entry` signature to match HA platform contract
    3. Ensure all entity property overrides match HA `Entity` base class types
    4. Verify `make typecheck` passes with zero errors
  - **Files**: custom_components/ev_trip_planner/sensor/*.py
  - **Done when**: `make typecheck` reports zero errors for sensor files
  - **Verify**: `make typecheck && echo GREEN_PASS`
  - **Commit**: `fix(spec3): fix 16 pyright errors in sensor.py entity classes`
  - _Requirements: NFR-7.A.5, FR-1.7_
  - _Design: design-by-convention (sensor pyright); NFR-7.A.5 + FR-1.7_

- [ ] 1.99 [YELLOW] Remove sensor.py transitional shim
  - **Do**:
    1. Delete `sensor.py`
    2. Verify HA platform discovery still loads `async_setup_entry` via `sensor/__init__.py` re-export (no edit needed because the new package re-exports the same public symbols: `async_setup_entry`, `TripPlannerSensor`, `EmhassDeferrableLoadSensor`, `TripSensor`, `TripEmhassSensor`)
    3. Verify `make test` and `make typecheck` pass
  - **Files**: custom_components/ev_trip_planner/sensor.py (delete)
  - **Done when**: No `sensor.py` exists; all imports resolve through package
  - **Verify**: `! test -f custom_components/ev_trip_planner/sensor.py && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_sensor*.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove sensor.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: design-by-convention (sensor shim removal); §4.6_


- [ ] V10 [VERIFY] Quality check: ruff check && pyright
  - **Do**: Run quality checks after sensor decomposition
  - **Verify**: `make lint && make typecheck`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint sensor`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, sensor)_

### 1.8 config_flow.py - Decomposition

- [ ] 1.100 [RED] Test: config_flow package re-exports 3 public names
  - **Do**: Write test importing `EVTripPlannerFlowHandler`, `EVTripPlannerOptionsFlowHandler`, `async_get_options_flow` from `custom_components.ev_trip_planner.config_flow`
  - **Files**: tests/unit/test_config_flow_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_config_flow_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - config_flow package must re-export 3 public names`
  - _Requirements: AC-2.4_
  - _Design: design-by-convention (config_flow decomp; design.md §3 has no config_flow section); §4.6_

- [ ] 1.101 [GREEN] Scaffold config_flow/ with re-exports and split by flow type
  - **Do**:
    1. Create `custom_components/ev_trip_planner/config_flow/` directory
    2. Create `__init__.py` re-exporting 3 public names
    3. Split into `config_flow/main.py` (EVTripPlannerFlowHandler) and `config_flow/options.py` (EVTripPlannerOptionsFlowHandler)
    4. Keep `config_flow.py` as transitional shim
  - **Files**: custom_components/ev_trip_planner/config_flow/__init__.py, config_flow/*.py, config_flow.py (shim)
  - **Done when**: 3 names importable; existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_config_flow_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold config_flow/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: design-by-convention (config_flow decomp); §4.6_

- [ ] 1.102 [YELLOW] Remove config_flow.py transitional shim
  - **Do**:
    1. Delete `config_flow.py`
    2. Verify `make test` passes
  - **Files**: custom_components/ev_trip_planner/config_flow.py (delete)
  - **Done when**: No `config_flow.py` exists; all imports resolve through package
  - **Verify**: `! test -f custom_components/ev_trip_planner/config_flow.py && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_config_flow*.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove config_flow.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: design-by-convention (config_flow shim removal); §4.6_



- [ ] V11 [VERIFY] Quality check: ruff check && pyright after config_flow
  - **Do**: Run quality checks after config_flow decomposition
  - **Verify**: `make lint && make typecheck`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint config-flow`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, config_flow)_

### 1.9 presence_monitor.py - Decomposition

- [ ] 1.103 [RED] Test: presence_monitor package re-exports PresenceMonitor
  - **Do**: Write test importing `PresenceMonitor` from `custom_components.ev_trip_planner.presence_monitor`
  - **Files**: tests/unit/test_presence_monitor_imports.py
  - **Done when**: Test exists and fails
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_presence_monitor_imports.py -v 2>&1 | grep -q "FAILED\|FAIL" && echo RED_PASS`
  - **Commit**: `test(spec3): red - presence_monitor package must re-export PresenceMonitor`
  - _Requirements: AC-2.4_
  - _Design: design-by-convention (presence_monitor decomp; design.md §3 has no presence_monitor section); §4.6_

- [ ] 1.104 [GREEN] Scaffold presence_monitor/ with re-exports
  - **Do**:
    1. Create `custom_components/ev_trip_planner/presence_monitor/` directory
    2. Create `__init__.py` re-exporting `PresenceMonitor` from `monitor.py`
    3. Move `PresenceMonitor` class to `presence_monitor/monitor.py`
    4. Keep `presence_monitor.py` as transitional shim
  - **Files**: custom_components/ev_trip_planner/presence_monitor/__init__.py, presence_monitor/monitor.py, presence_monitor.py (shim)
  - **Done when**: `PresenceMonitor` importable; existing tests pass
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_presence_monitor_imports.py -v && echo GREEN_PASS`
  - **Commit**: `refactor(spec3): scaffold presence_monitor/ package with re-exports`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: design-by-convention (presence_monitor decomp); §4.6_

- [ ] 1.105 [YELLOW] Remove presence_monitor.py transitional shim
  - **Do**:
    1. Delete `presence_monitor.py`
    2. Verify `vehicle_controller.py` TYPE_CHECKING import (`from .presence_monitor import PresenceMonitor`) still resolves — no edit needed because the new `presence_monitor/__init__.py` re-exports the same symbol
    3. Verify `make test` passes
  - **Files**: custom_components/ev_trip_planner/presence_monitor.py (delete)
  - **Done when**: No `presence_monitor.py` exists; all imports resolve through package
  - **Verify**: `! test -f custom_components/ev_trip_planner/presence_monitor.py && PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_presence_monitor*.py -v && echo YELLOW_PASS`
  - **Commit**: `refactor(spec3): remove presence_monitor.py transitional shim`
  - _Requirements: AC-2.5_
  - _Design: design-by-convention (presence_monitor shim removal); §4.6_



- [ ] V12 [VERIFY] Quality check: ruff check && pyright after presence_monitor
  - **Do**: Run quality checks after presence_monitor decomposition
  - **Verify**: `make lint && make typecheck`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(spec3): pass quality checkpoint presence-monitor`
  - _Requirements: NFR-7.B (Bar B monotone progress), NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, presence_monitor)_


## Phase 2: Additional Testing

Focus: Integration testing across decomposed packages, E2E verification, full quality validation.
- [ ] 2.1 [VERIFY] Run full test suite: make test-cover with 100% coverage
  - **Do**: Run `make test-cover` and verify 100% coverage maintained
  - **Verify**: `make test-cover && echo VERIFY_PASS`
  - **Done when**: All 1,820+ tests pass with 100% coverage
  - **Commit**: `chore(spec3): pass full test suite with 100% coverage`
  - _Requirements: NFR-4.1, NFR-4.4_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] 2.2 [VERIFY] Run E2E tests: make e2e
  - **Do**: Run `make e2e` to verify all 30 E2E tests pass
  - **Verify**: `make e2e && echo VERIFY_PASS`
  - **Done when**: All 30 E2E tests pass
  - **Commit**: `chore(spec3): pass all 30 E2E tests`
  - _Requirements: NFR-4.2_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] 2.3 [VERIFY] Run E2E SOC tests: make e2e-soc
  - **Do**: Run `make e2e-soc` to verify all 10 SOC tests pass
  - **Verify**: `make e2e-soc && echo VERIFY_PASS`
  - **Done when**: All 10 SOC E2E tests pass
  - **Commit**: `chore(spec3): pass all 10 SOC E2E tests`
  - _Requirements: NFR-4.3_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] 2.4 [VERIFY] Verify zero pyright errors across entire package
  - **Do**: Run `make typecheck` and verify zero errors (including previously-16 sensor.py errors)
  - **Verify**: `make typecheck && echo VERIFY_PASS`
  - **Done when**: Zero pyright errors across entire package
  - **Commit**: `chore(spec3): verify zero pyright errors across entire package`
  - _Requirements: NFR-7.A.5_
  - _Design: §7 + §4.4 (final pyright check)_

- [ ] 2.5 [VERIFY] Verify lint-imports contracts pass
  - **Do**: Run `make import-check` and verify all 7 lint-imports contracts pass
  - **Verify**: `make import-check && echo VERIFY_PASS`
  - **Done when**: All 7 import contracts pass, zero violations
  - **Commit**: `chore(spec3): verify all 7 lint-imports contracts pass`
  - _Requirements: NFR-7.A.4_
  - _Design: §4.4 (lint-imports Contracts)_

- [ ] 2.6 [VERIFY] Verify SOLID metrics: solid_metrics.py reports 5/5 PASS
  - **Do**: Run `scripts/solid_metrics.py` and verify S, O, L, I, D all green
  - **Verify**: `.venv/bin/python scripts/solid_metrics.py 2>&1 | grep -E "S:|O:|L:|I:|D:" | grep -v "PASS" | grep -v "^$" | wc -l | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: All 5 SOLID letters PASS for every class
  - **Commit**: `chore(spec3): verify 5/5 SOLID letters PASS`
  - _Requirements: NFR-7.A.1_
  - _Design: §7 + §2 (final SOLID metrics)_

- [ ] 2.7 [VERIFY] Verify principles: principles_checker.py reports 0 violations
  - **Do**: Run `scripts/principles_checker.py` and verify DRY, KISS, YAGNI, LoD, CoI all 0 violations
  - **Verify**: `.venv/bin/python scripts/principles_checker.py 2>&1 | grep -c "violation" | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: 0 violations across all 5 principles
  - **Commit**: `chore(spec3): verify 0 violations across all principles`
  - _Requirements: NFR-7.A.2_
  - _Design: §7 (Per-decomposition validation gate)_

- [ ] 2.8 [VERIFY] Verify antipattern checker: 0 Tier A violations
  - **Do**: Run `scripts/antipattern_checker.py` and verify 0 Tier A violations (25 patterns)
  - **Verify**: `.venv/bin/python scripts/antipattern_checker.py 2>&1 | grep -c "violation" | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: 0 Tier A antipattern violations
  - **Commit**: `chore(spec3): verify 0 Tier A antipattern violations`
  - _Requirements: NFR-7.A.3_
  - _Design: §7 (Per-decomposition validation gate)_


## Phase 3: Quality Gates

Focus: Comprehensive quality-gate verification, SOLID metrics validation per-package, AC checklist, bug-fix verification.

### Final-Sequence Checkpoints (V4 → V5 → V6) per phase-rules.md

- [ ] 3.0 [VERIFY] Install Tier A analysis tools (radon, jscpd)
  - **Do**:
    1. Install radon into venv: `.venv/bin/pip install radon`
    2. Verify jscpd available (Node, run via npx — no global install required): `npx --yes jscpd --version`
    3. Verify both tools resolve: `python -m radon --version && npx --yes jscpd --version`
  - **Files**: (none — environment install only)
  - **Done when**: `python -m radon` and `npx --yes jscpd` both runnable
  - **Verify**: `python -m radon --version >/dev/null && npx --yes jscpd --version >/dev/null && echo PASS`
  - **Commit**: None
  - _Requirements: NFR-3.1, NFR-7.A.2_
  - _Design: §6.1 (pre-condition tooling)_

- [ ] V_final_a [VERIFY] V4 — Full local CI
  - **Do**: Run `make quality-gate-ci && make test-cover && make e2e && make e2e-soc && make import-check && make typecheck && make lint`
  - **Verify**: All exit 0
  - **Done when**: Full local CI green, 100% coverage, 1820+ tests pass, 40 E2E pass, lint-imports 0 violations, pyright 0 errors
  - **Commit**: `chore(spec3): pass full local CI`
  - _Requirements: NFR-7.A.1, NFR-7.A.2, NFR-7.A.3, NFR-7.A.4, NFR-7.A.5_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] V_final_b [VERIFY] V5 — CI pipeline passes after push
  - **Do**: Push branch, run `gh pr checks --watch`
  - **Verify**: `gh pr checks` shows all ✓
  - **Done when**: GitHub Actions CI green for spec/3-solid-refactor → epic/tech-debt-cleanup
  - **Commit**: None
  - _Requirements: NFR-7.A_
  - _Design: §6.3 (checkpoint commits)_

- [ ] V_final_c [VERIFY] V6 — AC checklist programmatic verification
  - **Do**: For each AC in requirements.md (AC-1.1 to AC-13.5), run the corresponding verification command and record PASS/FAIL in `chat.md`. Specifically verify:
    - AC-1.1: `find custom_components/ev_trip_planner -name '*.py' -exec wc -l {} \; | awk '$1 > 500'` returns 0 lines
    - AC-1.2: 9 god modules decomposed (grep for old paths in tests)
    - AC-1.3: `radon cc custom_components/ev_trip_planner -nb` no grade B/C/D/E/F
    - AC-2.4: Public API imports unchanged (grep tests for `from custom_components.ev_trip_planner import`)
    - AC-4.7: solid_metrics.py reports ISP results
    - AC-5.1-5.5: DRY consolidations complete
    - AC-10.3: `pytest tests/unit/test_single_trip_hora_regreso_past.py` 3 assertions pass with values 96.0, 96.0, 92.0
    - AC-13.1: `grep -A 1 'previous_arrival = _ensure_aware' custom_components/ev_trip_planner/calculations/windows.py` shows no `+ timedelta(hours=return_buffer_hours)`
  - **Verify**: All AC verifications PASS
  - **Done when**: AC checklist complete with 0 FAILs
  - **Commit**: None
  - _Requirements: ALL AC-*_
  - _Design: §6.3 (checkpoint commits)_

### E2E Verification on STAGING (VE0..VE3 per CLAUDE.md staging rules — Docker :8124)

- [ ] VE0 [VERIFY] Build selector map (ui-map-init)
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, ui-map-init, home-assistant-best-practices
  - **Do**: Follow `${CLAUDE_PLUGIN_ROOT}/skills/e2e/ui-map-init.skill.md` — open Playwright MCP session to `http://localhost:8124`, explore HA UI (Settings → Devices, Integrations, Lovelace dashboards), write `ui-map.local.md` to `specs/3-solid-refactor/ui-map.local.md`. Note: HA uses web components with Shadow DOM — use `browser_evaluate` patterns from `home-assistant-best-practices` skill, NOT `browser_snapshot`.
  - **Verify**: `test -f specs/3-solid-refactor/ui-map.local.md && grep -q 'lovelace\|dashboard' specs/3-solid-refactor/ui-map.local.md && echo PASS`
  - **Done when**: ui-map.local.md exists with at least 3 routes (overview, integrations, ev-trip-planner panel)
  - **Commit**: None
  - _Requirements: NFR-7.A_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] VE1 [VERIFY] E2E startup: launch staging Docker HA
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, home-assistant-best-practices
  - **Do**:
    1. Start staging: `make staging-up` (Docker on :8124, persistent config at ~/staging-ha-config/)
    2. Poll http://localhost:8124 until 200 (timeout 60s — HA boot is slow)
    3. Verify ev_trip_planner integration loaded: `curl -sf http://localhost:8124/api/states | jq -r '.[] | select(.entity_id | startswith("sensor.ev_trip_planner"))' | head -1`
  - **Verify**: `curl -sf http://localhost:8124 -o /dev/null && curl -sf -H "Authorization: Bearer $HA_TOKEN" http://localhost:8124/api/ 2>&1 | grep -q "API running" && echo PASS`
  - **Done when**: Staging HA up on :8124, ev_trip_planner integration loaded
  - **Commit**: None
  - _Requirements: NFR-7.A_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] VE2 [VERIFY] E2E check: add trip via UI and verify sensor updates
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session, selector-map, home-assistant-best-practices
  - **Do**:
    0. Export `HA_TOKEN` from a long-lived access token created via the staging HA UI (Profile → Long-Lived Access Tokens). If `$HA_TOKEN` is unset, fail fast: `[ -n "$HA_TOKEN" ] || { echo "ERROR: HA_TOKEN unset — create long-lived token at http://localhost:8124/profile/security and export it" >&2; exit 1; }`
    1. Read `specs/3-solid-refactor/ui-map.local.md` for selectors
    2. Navigate to http://localhost:8124 root (NOT goto to internal route)
    3. Click sidebar → ev-trip-planner panel via UI navigation
    4. Add a punctual trip: fill destination, datetime, kWh_needed; click submit
    5. Verify sensor state updated: poll `curl -s http://localhost:8124/api/states/sensor.ev_trip_planner_<trip_id>` until JSON shows new trip
    6. Verify dashboard renders: navigate to ev-trip-planner Lovelace view, confirm trip card appears
  - **Verify**: `curl -sf -H "Authorization: Bearer $HA_TOKEN" http://localhost:8124/api/states 2>&1 | jq -e '.[] | select(.entity_id | startswith("sensor.ev_trip_planner_"))' >/dev/null && echo PASS`
  - **Done when**:
    - [ ] Navigated to panel via sidebar click (NOT page.goto to /config/ev_trip_planner)
    - [ ] Trip submission completed without error
    - [ ] sensor.ev_trip_planner_<trip_id> appears in /api/states
    - [ ] Dashboard view shows the new trip
    - [ ] No 404, login page, or unexpected URL during flow
  - **Commit**: `test(spec3): E2E VE2 verify trip-add flow on staging`
  - _Requirements: AC-2.1, AC-2.4 (public API + HA integration intact)_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] VE3 [VERIFY] E2E cleanup: stop staging
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Stop staging: `make staging-down`
    2. Verify port free: `! lsof -ti :8124`
  - **Verify**: `! lsof -ti :8124 && echo PASS`
  - **Done when**: No process on :8124
  - **Commit**: None
  - _Requirements: NFR-7.A_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

### Existing Per-Package Quality Gates (V1..V12 are decomposition checkpoints)

- [ ] 3.1 [VERIFY] Full local CI: lint + typecheck + test + e2e + quality-gate
  - **Do**:
    1. Run `make lint` and verify pass
    2. Run `make typecheck` and verify zero errors
    3. Run `make test-cover` and verify all tests pass with 100% coverage
    4. Run `make e2e` and verify all 30 E2E tests pass
    5. Run `make e2e-soc` and verify all 10 SOC tests pass
    6. Run `make quality-gate-ci` (quality gate without E2E) and verify all metrics
  - **Verify**: All 6 commands exit 0
  - **Done when**: Full local CI pipeline passes
  - **Commit**: `chore(spec3): pass full local CI`
  - _Requirements: NFR-4, NFR-7.A_
  - _Design: §7 (Per-decomposition validation gate, final-acceptance)_

- [ ] 3.2 [VERIFY] Run quality-gate diff vs baseline
  - **Do**:
    1. Run `make quality-gate` again and compare to baseline captured in task 1.1
    2. Document improvements in `.progress.md`
    3. Verify SOLID metrics improved (or maintained at ceiling)
    4. Verify DRY/KISS violations decreased to 0
    5. Verify anti-pattern violations decreased to 0
  - **Verify**: Quality-gate output shows improvement or maintenance of passing metrics
  - **Done when**: Quality-gate diff documented; Bar B per-checkpoint thresholds met
  - **Commit**: `chore(spec3): document quality-gate improvement vs baseline`
  - _Requirements: NFR-7.B_
  - _Design: §7 + Bar B per-checkpoint progress_

- [ ] 3.3 [VERIFY] SOLID metrics per-package: verify LCOM4, verb diversity, ISP for each decomposed package
  - **Do**:
    1. Run `solid_metrics.py` scoped to `calculations/` - verify S letter PASS
    2. Run `solid_metrics.py` scoped to `vehicle/` - verify S letter PASS
    3. Run `solid_metrics.py` scoped to `dashboard/` - verify S letter PASS
    4. Run `solid_metrics.py` scoped to `emhass/` - verify S letter PASS
    5. Run `solid_metrics.py` scoped to `trip/` - verify S letter PASS
    6. Run `solid_metrics.py` scoped to `services/` - verify S letter PASS
    7. Run `solid_metrics.py` scoped to `sensor/` - verify S letter PASS
    8. Run `solid_metrics.py` scoped to `config_flow/` - verify S letter PASS
    9. Run `solid_metrics.py` scoped to `presence_monitor/` - verify S letter PASS
  - **Verify**: All 9 packages pass S letter (LCOM4 <= 2, verb diversity <= 5)
  - **Done when**: Every package passes SOLID metrics individually
  - **Commit**: `chore(spec3): verify SOLID metrics per-package`
  - _Requirements: NFR-1, NFR-7.A.1_
  - _Design: §7 + §2 (SOLID per-package)_

- [ ] 3.4 [VERIFY] Per-package LOC verification: no source file > 500 LOC
  - **Do**:
    1. `find custom_components/ev_trip_planner -name "*.py" -not -path "*/templates/*" -exec wc -l {} +`
    2. Verify each output line has LOC <= 500
    3. Report any file exceeding 500 LOC
  - **Verify**: `find custom_components/ev_trip_planner -name "*.py" -not -path "*/templates/*" -exec wc -l {} + | awk '{if ($1 > 500) print $0}' | wc -l | grep -q '^0$' && echo VERIFY_PASS`
  - **Done when**: Every source file <= 500 LOC
  - **Commit**: `chore(spec3): verify no source file exceeds 500 LOC`
  - _Requirements: AC-1.1_
  - _Design: §7 + FR-1.1 (file ≤ 500 LOC)_

- [ ] 3.5 [VERIFY] Mutation config validation: verify all module paths in pyproject.toml exist
  - **Do**:
    1. Run `mutmut run --paths-to-mutate=custom_components/ev_trip_planner --dry-run`
    2. Verify no `KeyError` or path-not-found errors
    3. Verify all old module paths removed, all new sub-module paths present
  - **Verify**: `.venv/bin/mutmut run --paths-to-mutate=custom_components/ev_trip_planner --dry-run 2>&1 | grep -c "KeyError" | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: mutmut runs without path errors
  - **Commit**: `chore(spec3): validate mutation config paths`
  - _Requirements: FR-5.4_
  - _Design: §4.7 (Mutation Config Path-Rename Mapping)_

- [ ] 3.6 [VERIFY] Per-package DRY violation verification: sliding-window similarity = 0
  - **Do**:
    1. Run `jscpd` or `simian` over `custom_components/ev_trip_planner/`
    2. Verify 0 duplications >= 5 consecutive lines across files
    3. Verify `validate_hora` in exactly one location
    4. Verify `is_trip_today` in exactly one location
    5. Verify `calculate_day_index` in exactly one location
  - **Verify**: `npx --yes jscpd --min-tokens 50 --mode python custom_components/ev_trip_planner/ 2>&1 | grep -c "duplicate" | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: DRY = 0 violations
  - **Commit**: `chore(spec3): verify DRY = 0 violations`
  - _Requirements: NFR-2, AC-5.1-5.3_
  - _Design: §6.2 Step 0.5 (DRY validation)_

- [ ] 3.7 [VERIFY] Cyclomatic complexity: all functions <= 10
  - **Do**: Run `radon cc -a custom_components/ev_trip_planner/` and verify zero rank-lines with rank C/D/E/F (i.e., all functions cc <= 10 → rank A/B only). The regex anchors on the rank-line prefix (`^\s+[CDEF] `) to avoid matching uppercase letters in file paths or function names.
  - **Verify**: `.venv/bin/python -m radon cc -a custom_components/ev_trip_planner/ 2>&1 | grep -E "^\s+[CDEF] " | wc -l | tr -d ' ' | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: All functions have cyclomatic complexity <= 10 (zero rank C/D/E/F lines)
  - **Commit**: `chore(spec3): verify cyclomatic complexity <= 10`
  - _Requirements: AC-1.3, NFR-3.1_
  - _Design: §7 + NFR-3.1 (KISS)_

- [ ] 3.8 [VERIFY] Nesting depth: all functions <= 4
  - **Do**: Walk every `.py` file under `custom_components/ev_trip_planner/` with an AST nesting-depth script and verify max nesting depth <= 4. Counted constructs: `If`, `For`, `While`, `With`, `Try` (radon has no `nc` subcommand, so we use stdlib `ast`). Steps:
    1. Create `scripts/check_nesting.py` (committed in this task) that walks the tree and exits 0 if max depth <= 4, else 1.
    2. Run it via the venv interpreter.
  - **Files**: scripts/check_nesting.py
  - **Verify**: `.venv/bin/python scripts/check_nesting.py custom_components/ev_trip_planner 4 && echo VERIFY_PASS`
  - **Done when**: All functions have nesting depth <= 4 across counted constructs (If/For/While/With/Try)
  - **Commit**: `chore(spec3): verify nesting depth <= 4`
  - _Requirements: AC-1.4, NFR-3.2_
  - _Design: §7 + NFR-3.2 (nesting)_

- [ ] 3.9 [VERIFY] deptry: zero broken imports
  - **Do**: Run `make unused-deps` to verify zero broken imports
  - **Verify**: `make unused-deps && echo VERIFY_PASS`
  - **Done when**: `deptry` reports zero broken-import findings
  - **Commit**: `chore(spec3): verify zero broken imports via deptry`
  - _Requirements: AC-2.7_
  - _Design: §4.4 (lint-imports / deptry)_

- [ ] 3.10 [VERIFY] Bug fixes verified: [BUG-001] and [BUG-002] regression tests pass
  - **Do**: Run the bug regression tests
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_ventana_horas_invariant.py tests/unit/test_previous_arrival_invariant.py tests/unit/test_single_trip_hora_regreso_past.py -v && echo VERIFY_PASS`
  - **Done when**: All bug regression tests pass with corrected values
  - **Commit**: `chore(spec3): verify [BUG-001] and [BUG-002] regression tests pass`
  - _Requirements: AC-10.1, AC-10.2, AC-10.3_
  - _Design: §5.1 (bug fix regression)_

- [ ] 3.11 [VERIFY] Verify 7 lazy sensor imports eliminated
  - **Do**: Grep for `from .sensor import` in trip-management code (trip/ package) and verify zero matches
  - **Verify**: `grep -rc 'from \.sensor import' custom_components/ev_trip_planner/trip/ | grep -v ':0$' | wc -l | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: Zero `from .sensor import` in trip-management code
  - **Commit**: `chore(spec3): verify 7 lazy sensor imports eliminated`
  - _Requirements: AC-8.1, AC-8.2, AC-8.3_
  - _Design: §4.2 (SensorCallbackRegistry)_

- [ ] 3.12 [VERIFY] Verify dashboard templates load at runtime
  - **Do**: Import `import_dashboard` and verify templates load from `dashboard/templates/`
  - **Verify**: `PYTHONPATH=. .venv/bin/python -c "
from pathlib import Path
from custom_components.ev_trip_planner.dashboard._paths import TEMPLATES_DIR
assert TEMPLATES_DIR.is_dir(), f'TEMPLATES_DIR {TEMPLATES_DIR} not a directory'
assert len(list(TEMPLATES_DIR.glob('*'))) == 11, f'Expected 11 templates, found {len(list(TEMPLATES_DIR.glob(\"*\")))}'
print('VERIFY_PASS')
"`
  - **Done when**: `TEMPLATES_DIR` resolves to valid directory with 11 template files
  - **Commit**: `chore(spec3): verify dashboard templates load correctly`
  - _Requirements: AC-7.1, AC-7.2, AC-7.3_
  - _Design: §3.4 + §4.3 (dashboard pathlib runtime check)_

- [ ] 3.13 [VERIFY] Public API surface verification: all preserved names importable
  - **Do**: For each god module, verify all public names are importable:
    - `EMHASSAdapter` from `emhass`
    - `TripManager`, `CargaVentana`, `SOCMilestoneResult` from `trip`
    - 10 functions from `services`
    - `import_dashboard`, `is_lovelace_available`, `DashboardImportResult` + 4 exceptions from `dashboard`
    - `VehicleController`, `VehicleControlStrategy`, `create_control_strategy` from `vehicle`
    - 20 names from `calculations`
    - `async_setup_entry`, 4 Entity classes from `sensor`
    - 3 names from `config_flow`
    - `PresenceMonitor` from `presence_monitor`
  - **Verify**: Shell script imports each name; exit 0 if all resolve
  - **Done when**: All 50+ preserved public names importable from new package paths
  - **Commit**: `chore(spec3): verify all preserved public names importable`
  - _Requirements: AC-2.4, AC-2.5_
  - _Design: §4.5 (Public API __all__ Mechanics)_

- [ ] 3.14 [VERIFY] Transitional shim cleanup verification
  - **Do**: Verify no transitional shim files remain
  - **Verify**: `for f in calculations.py vehicle_controller.py dashboard.py emhass_adapter.py trip_manager.py services.py sensor.py config_flow.py presence_monitor.py; do test -f custom_components/ev_trip_planner/$f && echo "SHIM REMAINS: $f" && exit 1; done && echo VERIFY_PASS`
  - **Done when**: No transitional shim files remain
  - **Commit**: `chore(spec3): verify all transitional shims removed`
  - _Requirements: AC-2.5_
  - _Design: §4.6 (Test Import Migration final state)_

- [ ] 3.15 [VERIFY] AC checklist: programmatically verify each acceptance criterion
  - **Do**:
    1. AC-1.1: `find custom_components/ev_trip_planner -name "*.py" -exec wc -l {} + | awk '{print $1}' | sort -rn | head -1` <= 500
    2. AC-1.2: 9 god modules decomposed (verify original files deleted)
    3. AC-1.3: radon cc <= 10 for all functions
    4. AC-1.4: radon nc <= 4 for all functions
    5. AC-1.5: `register_services` <= 100 LOC (check services/handlers.py)
    6. AC-1.6: `_populate_per_trip_cache_entry` extracted (check emhass/_cache_entry_builder.py)
    7. AC-2.4: All public names importable from packages (shell-test each)
    8. AC-2.5: No transitional shim files remain
    9. AC-3.1: `make test` passes >= 1,820 tests
    10. AC-4.1: LCOM4 <= 2 for all classes (solid_metrics.py)
    11. AC-4.5: Zero circular cycles (lint-imports)
    12. AC-4.6: Type-hint coverage >= 90%
    13. AC-4.7: ISP check implemented (solid_metrics.py)
    14. AC-5.1-5.3: DRY = 0 violations (principles_checker.py)
    15. AC-6.1: register_services cc <= 10
    16. AC-7.1-7.3: Templates load (e2e-soc passes)
    17. AC-8.1-8.3: Zero lazy sensor imports
    18. AC-10.1-10.5: Bug fixes verified
  - **Verify**: `bash -e -c 'find custom_components/ev_trip_planner -name "*.py" -exec wc -l {} + | awk "{if (\$1 > 500) {print; exit 1}}" && make test && make typecheck && make import-check && make e2e-soc' && echo VERIFY_PASS`
  - **Done when**: Every acceptance criterion verified via automated checks
  - **Commit**: `chore(spec3): verify all acceptance criteria`
  - _Requirements: All AC-*_
  - _Design: §7 (AC checklist)_

- [ ] 3.16 [VERIFY] Verify zero circular import cycles
  - **Do**: Run `make import-check` (which invokes `lint-imports` against all 7 contracts). The wrapper exits non-zero on any contract violation, so we use exit-code-based verification rather than a fragile grep on output text.
  - **Verify**: `make import-check && echo VERIFY_PASS`
  - **Done when**: All 7 import contracts pass
  - **Commit**: `chore(spec3): verify zero circular import cycles`
  - _Requirements: FR-3.1, NFR-7.A.4_
  - _Design: §4.4 (lint-imports Contracts)_

- [ ] 3.17 [VERIFY] Verify KISS compliance: register_services() decomposed
  - **Do**: Check services/handlers.py for `register_services` function LOC and cyclomatic complexity
  - **Verify**: `python -m radon cc custom_components/ev_trip_planner/services/handlers.py -a && wc -l custom_components/ev_trip_planner/services/handlers.py && echo VERIFY_PASS`
  - **Done when**: `register_services` <= 100 LOC, cc <= 10
  - **Commit**: `chore(spec3): verify KISS compliance for register_services`
  - _Requirements: AC-1.5, AC-6.1, NFR-3.1, NFR-3.3_
  - _Design: §3.3 (services KISS)_


## Phase 4: PR Lifecycle

Focus: PR creation, CI monitoring, review resolution, final validation.
- [ ] 4.1 [VERIFY] Verify current branch is feature branch
  - **Do**: Check `git branch --show-current` - must be `spec/3-solid-refactor` (or equivalent feature branch)
  - **Verify**: `git branch --show-current | grep -q "^spec/" && echo VERIFY_PASS`
  - **Done when**: On a feature branch, not on main or epic/tech-debt-cleanup
  - **Commit**: None
  - _Requirements: NFR-7.A (final deliverable)_
  - _Design: §6.3 (checkpoint commits)_

- [ ] 4.2 [VERIFY] Push branch and create PR
  - **Do**:
    1. Push branch: `git push -u origin spec/3-solid-refactor`
    2. Create PR targeting `epic/tech-debt-cleanup` using gh CLI
    3. PR title: `refactor(tech-debt): decompose 9 god modules into SOLID packages`
    4. PR body: summary of changes, SOLID metric improvements, bug fixes, package structure
    5. Add milestone/labels as appropriate for epic tracking
  - **Verify**: `gh pr view --json number,title,state | jq '.number' | grep -q '[0-9]' && echo VERIFY_PASS`
  - **Done when**: PR created and visible on GitHub
  - **Commit**: None
  - _Requirements: NFR-7.A (final deliverable)_
  - _Design: §6.3 (checkpoint commits / PR creation)_

- [ ] 4.3 [VERIFY] Monitor CI pipeline
  - **Do**:
    1. Wait for CI checks to complete: `gh pr checks --watch`
    2. If any check fails, read failure details: `gh pr checks`
    3. Fix issues locally: commit fixes, push
    4. Re-verify: `gh pr checks --watch`
  - **Verify**: `gh pr checks | grep -v "✓" | grep -v "Pending" | grep -v "loading" | wc -l | grep -q "^0$" && echo VERIFY_PASS`
  - **Done when**: All CI checks show green (✓)
  - **Commit**: `fix(spec3): address CI failures` (only if fixes needed)
  - _Requirements: NFR-7.A (final deliverable)_
  - _Design: §6.3 (checkpoint commits)_

- [ ] 4.4 [VERIFY] Final validation: zero regressions, modularity, real-world verification
  - **Do**:
    1. Re-run `make test-cover` - 100% coverage, no regressions
    2. Re-run `make e2e` and `make e2e-soc` - all E2E tests pass
    3. Re-run `make quality-gate-ci` - all quality gates pass
    4. Verify code is modular: each file <= 500 LOC, each class <= 20 public methods
    5. Verify SOLID metrics: 5/5 letters PASS
    6. Check PR for any unresolved review comments
  - **Verify**: All commands pass, PR has no unresolved comments
  - **Done when**: All quality gates pass, PR ready for merge
  - **Commit**: None
  - _Requirements: NFR-7.A, NFR-4.1, NFR-4.2, NFR-4.3_
  - _Design: §6.3 + §7 (final validation)_

- [ ] 4.5 [VERIFY] PR Lifecycle completion criteria
  - **Do**:
    1. All Phase 1-4 tasks complete (checked [x])
    2. All Phase 4 tasks complete
    3. CI checks all green
    4. No unresolved review comments
    5. Zero test regressions
    6. Code is modular and SOLID-compliant
  - **Verify**: Checklist items all true
  - **Done when**: Spec is complete - all criteria met
  - **Commit**: None
  - _Requirements: NFR-7.A (final deliverable)_
  - _Design: §6.3 (PR completion)_

## Notes

- **TDD approach**: All decomposition follows Red-Green-Yellow triplets. Each [RED] verifies expected behavior fails, each [GREEN] provides minimum code to pass, each [YELLOW] refactors while keeping tests green.
- **YELLOW skip rule**: YELLOW tasks are present when the preceding GREEN introduces ≥ 30 LOC or non-obvious structure. Skipped when GREEN body is a mechanical move/rename (no cleanup needed). 15/42 = 36% YELLOW reflects that most splits are file-moves of already-clean code.
- **Transition mechanism**: 3-phase test import migration per design.md section 4.6. Phase 1 (scaffold + shims) happens AT decomposition commits. Phase 2 (test import updates) happens in Phase 2 of tasks. Phase 3 (shim removal) happens during decomposition as noted.
- **Bug fixes**: [BUG-001] ventana_horas and [BUG-002] previous_arrival co-fixed in calculations decomposition (tasks 1.15-1.19). [BUG-003] __file__ path fixed in dashboard pre-condition (tasks 1.38-1.41).
- **No CodeRabbit auto-wait**: PR creation is the last automated step (per process constraints).
- **Gito reviews**: Via /gito-review-with-spec only, after PR creation.
- **chat.md updates**: Every task must update chat.md before verify (per process constraints).
- **Mutation config**: Per-module paths updated in each decomposition commit (tasks 1.27, 1.37, 1.53, 1.65, 1.84, 1.94).
- **lint-imports key fix**: [tool.import-linter] -> [tool.importlinter] with 7 contracts (tasks 1.2-1.4).
- **solid_metrics.py ISP**: max_unused_methods_ratio check implemented (tasks 1.5-1.6).
- **DRY consolidation**: validate_hora, is_trip_today consolidated into utils.py before decompositions (tasks 1.7-1.8).
- **SensorCallbackRegistry**: Replaces 7 lazy from .sensor import calls in trip-management (tasks 1.68-1.69, 1.73).
- **Dependency order**: calculations -> vehicle -> dashboard -> emhass -> trip -> services -> sensor -> config_flow -> presence_monitor.
- **Step 0.5 pre-flight order** (per design.md §6.2, execution order follows task IDs): lint-imports config (1.2-1.4) → ISP check (1.5-1.6) → DRY consolidation (1.7-1.8) → dashboard `__file__` pre-condition (1.38-1.41). Justification: lint-imports config + ISP implementation come first because they are zero-coupling infrastructure additions (new config + new metric); DRY consolidation follows because it modifies multiple modules and benefits from lint-imports already enforcing layering, which catches accidental cross-package consolidation regressions. Dashboard `__file__` must be fixed before `dashboard/` decomposition writes pathlib paths.
- **VE tasks (STAGING, not E2E)**: VE0..VE3 use STAGING HA (Docker on :8124) per CLAUDE.md rules. E2E tests (`make e2e`, `make e2e-soc` on :8123 via `hass` direct) are validated by V_final_a/b and Phase 2 tasks 2.2/2.3. VE tasks exist to validate real-world dashboard/UI flow after decomposition.

## Dependencies

```
Phase 1 (TDD Cycles, 9 decomp packages) → Phase 2 (Additional Tests) → Phase 3 (Quality Gates: V_final_a → V_final_b → V_final_c → VE0 → VE1 → VE2 → VE3 → per-package gates) → Phase 4 (PR Lifecycle)
```

**Decomposition order** (mandatory per design.md §6.2):
calculations → vehicle → dashboard → emhass → trip → services → sensor → config_flow → presence_monitor

**Step 0.5 pre-flight** must complete BEFORE any decomposition (executed in task-ID order):
lint-imports config (1.2-1.4) → ISP check (1.5-1.6) → DRY consolidation (1.7-1.8) → dashboard __file__ pre-condition (1.38-1.41)

