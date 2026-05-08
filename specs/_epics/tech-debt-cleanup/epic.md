# Epic: Tech Debt Cleanup

## 1. Vision & Scope

Systematically eliminate all technical debt to achieve 100% SOLID compliance, zero Tier A/B antipatterns, 100% mutation kill rate, 100% test coverage, no `pragma: no cover`, zero warnings, clean architecture with separated tests, and all linters passing.

This epic touches all 18 source modules (~15,097 LOC), ~114 test files (~1,849 tests, including 10 TypeScript E2E), CI/CD, and Makefile infrastructure.

### ⚠️ Critical Environment Note

**ALL Python/bash commands in this project require virtual environment activation.** Before executing any `pip install`, `mutmut`, `pyright`, `pytest`, or other Python tool command, activate the venv:

```bash
. .venv/bin/activate
```

Every command in every spec assumes the venv is active. CI workflows must also handle venv activation. Failure to activate will result in tools not found or installing to the wrong Python.

### ⚠️ SOLID Threshold Phasing

The [`quality-gate.yaml`](.roo/skills/quality-gate/config/quality-gate.yaml) defines stricter SOLID thresholds than this epic's ARNs:

| Metric | ARN Target (Phase 1) | quality-gate.yaml (Phase 2) |
|--------|---------------------|---------------------------|
| Max LOC per class | 500 | 200 |
| Max public methods | 20 | 7 |
| Max arity | 5 | 5 |

This epic achieves Phase 1 (ARN targets). Phase 2 (quality-gate.yaml targets) is a future epic that further decomposes modules after the initial cleanup stabilizes. The quality-gate scripts should be configured with Phase 1 thresholds during this epic's execution.

## 2. Quality Gate Targets

### Layer 1: Test Execution (currently PASS)
| Metric | Current | Target |
|--------|---------|--------|
| pytest | 1,848 passed, 0 failures | 1,848+ passed, 0 failures |
| Coverage | 100% | 100% (via `--cov-fail-under`) |
| Mutation modules passing | 17/17 | 17/17 |
| Mutation kill rate | 48-49% | 100% |
| E2E | 30 passed | 30+ passed |

### Layer 2: Test Quality (currently FAIL)
| Rule | Current | Target |
|------|---------|--------|
| A1 (<=1 assertion) | 1,790 weak | < 200 (only legitimate smoke tests) |
| A8 (always-true) | 2 `assert True` | 0 |
| Similar pairs | 299 | < 50 |
| Diversity | borderline | edit distance >= 20 |

### Layer 3: Code Quality (currently FAIL)
| Metric | Current | Target |
|--------|---------|--------|
| pyright errors | 16 (sensor.py HA Entity overrides) | 0 |
| SOLID Tier A violations | 9 SRP, 1 OCP, 1 ISP | 0 |
| Antipatterns Tier A | 0 | 0 |
| `pragma: no cover` | 273 | 0 |
| Format issues | 15 files | 0 |
| Ruff errors | 0 (clean) | 0 |
| mypy | BROKEN | Replaced by pyright; `make check` calls pyright instead |
| Circular import cycles | 3 | 0 |

### Layer 4: Security (currently 0 tools installed)
| Tool | Priority | Target |
|------|----------|--------|
| bandit | Required | Installed + CI gate |
| gitleaks | Required | Installed + CI gate |
| pip-audit / safety | Required | Installed + CI gate |
| semgrep | Recommended | Installed (optional, no gate) |
| checkov | Recommended | Installed (optional, no gate) |
| deptry | Recommended | Installed — verifies import consistency after module splits |
| vulture | Recommended | Installed — detects dead code (complements Spec 1) |
| import-linter | Recommended | Installed — enforces dependency rules between modules, prevents new circular imports after Spec 3 splits |
| pre-commit | Recommended | Installed — automates quality checks before each commit, prevents regressions between specs |
| pytest-randomly | Recommended | Installed — randomizes test execution order, catches hidden inter-test dependencies after Spec 2 |
| pytest-xdist | Recommended | Installed — parallel test execution, speeds up CI 3-5x (critical for mutmut in Spec 5) |
| refurb | Optional | Installed — suggests Python modernizations during Spec 7 cleanup |

### TypeScript Quality (10 TS test files, not yet measured)
| Metric | Current | Target |
|--------|---------|--------|
| TypeScript compile | Unknown | Zero errors (`tsc --noEmit`) |
| ESLint (TS) | Unknown | Zero warnings |
| Format (prettier) | Unknown | Zero diff |

## 3. Epic ARNs (Architecture Requirement Notations)

### ARN-001: No module exceeds 500 LOC
Every source module must be <= 500 lines of code. God classes (`emhass_adapter.py` 2,730, `trip_manager.py` 2,503) MUST be split into focused modules.

### ARN-002: No class exceeds 20 public methods
All classes must have <= 20 public methods. Currently violated by `EMHASSAdapter` (41 methods), `TripManager` (49 methods), `VehicleController` (40 methods).

### ARN-003: No function exceeds 5 parameters
All function signatures must have <= 5 parameters. High-arity functions in `calculations.py`, `dashboard.py`, `emhass_adapter.py` must use dataclasses or parameter objects.

### ARN-004: Zero circular import cycles
All 3 circular dependency cycles must be eliminated via: `from __future__ import annotations`, dependency injection, or extracted protocols/interfaces.

### ARN-005: Zero dead code
All modules must be imported from at least one active code path. `schedule_monitor.py` (confirmed dead) must be deleted.

### ARN-006: No `pragma: no cover` in source
Every line of source code must be testable. IO error paths must be tested via `unittest.mock.patch` or pytest `raises`.

### ARN-007: No `assert True` in tests
Every test must assert real behavior. `assert True` must be replaced with actual assertions or removed.

### ARN-008: Tests organized by layer
Tests must be organized: `tests/unit/` (mocked unit tests), `tests/integration/` (real dependencies), `tests/e2e/` (browser-based). No flat structure.

**Naming convention**: `test_{module}_{aspect}.py` for unit tests, `test_{module}_integration.py` for integration tests. Shared fixtures in `tests/conftest.py` and `tests/fixtures/`. Test helpers in `tests/helpers/`.

**Excluded tests**: `tests_excluded_from_mutmut/` files must be evaluated — keep, move into new structure, or delete if obsolete.

### ARN-009: No unused imports or backup files
`.cover` files, `panel.js.bak/.old/.fixed` backups must be removed or moved to `_docs/`.

### ARN-010: All 17 modules meet per-module mutation thresholds
Each module's mutation kill rate must meet or exceed the target defined in `pyproject.toml`, with global floor of 100%.

## 4. Epic Decomposition

### Spec 0: Tooling Foundation
- **Goal**: Install missing tools, fix broken tooling, add Makefile targets, establish baseline metrics.
- **Prerequisites**: `.venv` exists and is activated for all commands.
- **Acceptance Criteria**:
  - AC-0.1: `bandit` installed and `make security-bandit` target works
  - AC-0.2: `pip-audit` or `safety` installed and `make security-audit` target works
  - AC-0.3: `gitleaks` binary installed and `make security-gitleaks` target works
  - AC-0.4: `semgrep` installed
  - AC-0.5: `mypy` broken — replaced with `pyright` as primary type checker; `make typecheck` runs pyright
  - AC-0.6: `make quality-gate` target added (orchestrates layers 1-4)
  - AC-0.7: `make mutation` shortcut target added
  - AC-0.8: `make typecheck` replaces `make mypy` (pyright only, mypy skipped); `make check` updated to call pyright instead of mypy
  - AC-0.9: All existing targets (`test`, `lint`, `format`, `e2e`, `check`) still work
  - AC-0.10: CI workflow updated to include quality-gate, mutation, and coverage gates
  - AC-0.11: Full quality-gate baseline snapshot saved to `_bmad-output/quality-gate/tech-debt-baseline.json`
  - AC-0.12: `deptry` installed — verifies import consistency (critical for post-Spec 3 validation)
  - AC-0.13: `vulture` installed — detects dead code (complements Spec 1)
  - AC-0.14: TypeScript tooling installed: `tsc`, ESLint for TS, Prettier
  - AC-0.15: `_bmad-output/` directory added to `.gitignore`
  - AC-0.16: Full antipattern_checker.py run against all modules; baseline findings documented
  - AC-0.17: `import-linter` installed with layer configuration (prevents new circular imports post-Spec 3)
  - AC-0.18: `pre-commit` installed with hooks for ruff, pyright, bandit, deptry (prevents regressions between specs)
  - AC-0.19: `pytest-randomly` installed (catches hidden inter-test dependencies after Spec 2 reorganization)
  - AC-0.20: `pytest-xdist` installed (parallel test execution, speeds up CI 3-5x, critical for mutmut in Spec 5)
  - AC-0.21: `refurb` installed (suggests Python modernizations for Spec 7 cleanup)
- **Interface Contracts**: Makefile targets must produce consistent exit codes (0 = pass, non-0 = fail) and machine-readable output for CI.
- **Estimated Size**: **0.5 story points**
- **Dependencies**: None (baseline, runs first)

### Spec 1: Dead Code & Artifact Elimination
- **Goal**: Remove all dead code, backup files, and stale artifacts. Reduce source LOC without changing behavior.
- **Acceptance Criteria**:
  - AC-1.1: `schedule_monitor.py` deleted (confirmed 0 source imports from any active code path)
  - AC-1.2: `tests/test_schedule_monitor.py` deleted (depends on schedule_monitor.py)
  - AC-1.3: `tests/test_coverage_edge_cases.py` updated to remove schedule_monitor import (line 529)
  - AC-1.4: All `*.py,cover` files (19 mutmut artifacts) added to `.gitignore` with pattern `*,cover`; existing tracked files removed via `git rm --cached`
  - AC-1.5: `frontend/panel.js.bak`, `frontend/panel.js.old`, `frontend/panel.js.fixed` deleted
  - AC-1.6: `dashboard.py` remains (3 active importers: config_flow, services, __init__), but verified as god class target for Spec 3
  - AC-1.7: `vehicle_controller.py` remains (14 references across 4 files, IS wired), but verified as god class target for Spec 3
  - AC-1.8: `make test` still passes (test count drops by ~15-20 due to deleted test files, new count: ~1,830)
  - AC-1.9: No new import errors introduced
  - AC-1.10: `[tool.quality-gate.mutation.modules.schedule_monitor]` removed from `pyproject.toml`
  - AC-1.11: `protocols.py,cover` removed (references non-existent file)
  - AC-1.12: `tests/ha-manual/` is a full HA test instance for E2E testing (NOT browser cache) — keep directory but clean up 63+ stale dashboard YAML versions (`ev-trip-planner-chispitas.yaml.{2..63}`)
  - AC-1.13: Deprecated Lovelace auto-import gated behind feature flag or removed (`async_import_dashboard_for_entry` call in `__init__.py:187`)
- **Interface Contracts**: No public APIs affected. `schedule_monitor.py` is never imported from production code.
- **Estimated Size**: **0.25 story points**
- **Dependencies**: None (can run in parallel with Spec 0)

### Spec 2: Test Architecture Reorganization
- **Goal**: Reorganize ~107 flat test files into unit/integration/E2E structure. Consolidate duplicate/weak tests. Eliminate `assert True`.
- **Acceptance Criteria**:
  - AC-2.1: Tests organized: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `tests/helpers/`
  - AC-2.2: 13 `test_trip_manager*.py` files consolidated into ≤ 3 focused test files
  - AC-2.3: 6 `test_config_flow*.py` files consolidated into ≤ 2 files
  - AC-2.4: Multiple `test_coverage*.py` files consolidated or replaced with behavior-driven tests
  - AC-2.5: 2 `assert True` violations fixed (replaced with real assertions or removed)
  - AC-2.6: Orphaned bug-finding tests (10 files) consolidated into behavior-driven regression tests
  - AC-2.7: `conftest.py` refactored: large fixture (~700 lines) split into module-scoped fixtures
  - AC-2.8: `make test` passes with >= 1,830 tests (post-Spec 1 baseline)
  - AC-2.9: All pytest path configuration updated in `pyproject.toml`
  - AC-2.10: `tests_excluded_from_mutmut/` files evaluated: kept, moved into new structure, or deleted
  - AC-2.11: Coverage source paths in `pyproject.toml` updated to reflect new test structure
- **Interface Contracts**: Test file paths change; `conftest.py` fixture signatures must remain compatible. Update `mutmut tests_dir` if paths change.
- **Estimated Size**: **1.5-2.0 story points**
- **Dependencies**: None (independent of Spec 0 and Spec 1; can run in parallel)

### Spec 3: SOLID Refactoring — God Classes
- **Goal**: Decompose god classes into focused modules. Eliminate all SOLID Tier A violations and 3 circular import cycles.
- **⚠️ Naming Conflict**: `custom_components/ev_trip_planner/dashboard/` already exists as a template directory with YAML/JS files. When splitting `dashboard.py` into a package, the templates must be moved to a subdirectory (e.g., `dashboard/templates/`) to avoid conflicts with Python package `__init__.py`.
- **Acceptance Criteria**:
  - AC-3.0: `dashboard.py` (1,285 LOC) split into:
    - `dashboard/__init__.py` — re-exports public API (import_dashboard, DashboardImportResult, is_lovelace_available)
    - `dashboard/importer.py` — import_dashboard, DashboardImportResult
    - `dashboard/template_manager.py` — YAML/JS template loading and management
    - `dashboard/templates/` — existing YAML/JS template files moved here
  - AC-3.0b: `vehicle_controller.py` (537 LOC) split into:
    - `vehicle/__init__.py` — re-exports VehicleController
    - `vehicle/strategy.py` — VehicleControlStrategy ABC + SwitchStrategy + ServiceStrategy
    - `vehicle/external.py` — ScriptStrategy + ExternalStrategy
    - `vehicle/controller.py` — VehicleController orchestrator
  - AC-3.0c: `calculations.py` (1,690 LOC) split into:
    - `calculations/__init__.py` — re-exports all public functions
    - `calculations/windows.py` — charging window calculations
    - `calculations/power.py` — power profile generation
    - `calculations/deficit.py` — deficit propagation
  - AC-3.1: `emhass_adapter.py` (2,730 LOC, 41 methods) split into:
    - `emhass/__init__.py` — re-exports EMHASSAdapter
    - `emhass/index_manager.py` — assign/release/cleanup of deferrable load indices
    - `emhass/load_publisher.py` — async_publish_all, cache management
    - `emhass/error_handler.py` — notification and error recovery
  - AC-3.2: `trip_manager.py` (2,503 LOC, 49 methods) split into:
    - `trip/__init__.py` — re-exports TripManager
    - `trip/crud.py` — add/update/delete/list trips
    - `trip/soc_calculator.py` — SOC calculation logic (calcular_ventana_carga, etc.)
    - `trip/power_profile.py` — power profile generation
    - `trip/schedule_generator.py` — deferrables schedule generation
  - AC-3.3: `services.py` (1,635 LOC, 27 functions) split into:
    - `services/__init__.py` — re-exports all service functions
    - `services/handlers.py` — service handler functions (grouped by domain)
    - `services/dashboard_helpers.py` — dashboard import helpers (renamed to avoid confusion with dashboard/ package)
    - `services/cleanup.py` — cleanup operations
  - AC-3.4: Circular import cycles eliminated:
    - `coordinator -> trip_manager -> sensor -> coordinator` → `from __future__ import annotations` in coordinator.py
    - `trip_manager -> vehicle_controller -> presence_monitor -> trip_manager` → TYPE_CHECKING imports
    - `trip_manager -> vehicle_controller -> trip_manager` → string type annotations
  - AC-3.5: All modules <= 500 LOC (new package sub-modules counted individually)
  - AC-3.6: All classes <= 20 public methods
  - AC-3.7: `make test` passes with >= 1,830 tests (post-Spec 1 baseline)
  - AC-3.8: No new pyright errors introduced
  - AC-3.9: `pyproject.toml` mutation config updated: old module entries replaced with new sub-module entries
  - AC-3.10: `pyproject.toml` `[tool.mutmut] paths_to_mutate` updated for new package structure
  - AC-3.11: `services.yaml` updated if service signatures change
  - AC-3.12: `deptry` run after all splits to verify no broken imports
  - AC-3.13: `ventana_horas` bug fix applied in calculations split (ROADMAP: inflated by away time in `calculations.py:545`)
- **Interface Contracts**: Public API surface of ALL split modules must remain identical — each package's `__init__.py` re-exports the original public API. Consumers import from the package name without needing to know internal structure. **Verified import graph — required re-exports per package:**

  | Package | Must Re-Export | Imported By |
  |---------|---------------|-------------|
  | `emhass/` | `EMHASSAdapter` | `__init__.py`, `coordinator.py`, `trip_manager.py` |
  | `trip/` | `TripManager` | `__init__.py`, `services.py`, `coordinator.py`, `presence_monitor.py` (TYPE_CHECKING), `vehicle_controller.py` (TYPE_CHECKING) |
  | `services/` | 10 functions: `async_cleanup_orphaned_emhass_sensors`, `async_cleanup_stale_storage`, `async_import_dashboard_for_entry`, `async_register_panel_for_entry`, `async_register_static_paths`, `async_remove_entry_cleanup`, `async_unload_entry_cleanup`, `build_presence_config`, `create_dashboard_input_helpers`, `register_services` | `__init__.py` |
  | `calculations/` | All public functions (11+ import sites in `emhass_adapter.py` and `trip_manager.py`) | `emhass_adapter.py`, `trip_manager.py` |
  | `dashboard/` | `import_dashboard`, `is_lovelace_available`, `DashboardImportResult` | `config_flow.py`, `services.py` |
  | `vehicle/` | `VehicleController` | `trip_manager.py` |

  **Internal imports within split modules** (e.g., `trip_manager.py` importing from `calculations.py` 7 times) must be updated to point to the correct sub-module after the split.
- **Estimated Size**: **8.0-12.0 story points**
- **Dependencies**: Spec 2 (test reorganization first, so tests don't break during refactoring)

### Spec 4: High-Arity & Parameter Refactoring
- **Goal**: Eliminate all functions with > 5 parameters. Replace long parameter lists with dataclasses or configuration objects.
- **Acceptance Criteria**:
  - AC-4.1: `calculate_multi_trip_charging_windows` (9 params) → uses dataclass
  - AC-4.2: `calculate_deficit_propagation` (9 params) → uses dataclass
  - AC-4.3: `calculate_power_profile_from_trips` (8 params) → uses dataclass
  - AC-4.4: `calculate_power_profile` (8 params) → uses dataclass
  - AC-4.5: `DashboardImportResult.__init__` (8 params) → uses dataclass or builder
  - AC-4.6: `_populate_per_trip_cache_entry` (12 params) → uses dataclass or builder
  - AC-4.7: All functions <= 5 params across all modules
  - AC-4.8: `make test` passes
  - AC-4.9: All type checks pass (pyright)
- **Interface Contracts**: Parameter order and names may change — update all callers. Dataclass fields must be named consistently.
- **Estimated Size**: **0.5 story points**
- **Dependencies**: Must run AFTER Spec 3 for `calculations`, `dashboard`, and `emhass_adapter` modules (their functions move to new files during the split). Can run in parallel with Spec 2 for other modules.

### Spec 5: Mutation Score Ramp (49% → 100%)
- **Goal**: Incrementally raise mutation kill rate from ~49% to 100% across all modules.
- **Acceptance Criteria**:
  - AC-5.1: All modules meet or exceed target kill rate from `pyproject.toml`
  - AC-5.2: Global kill rate >= 100%
  - AC-5.3: Per-module status all changed from `"in_progress"` to `"passing"`
  - AC-5.4: `make mutation` passes
  - AC-5.5: `make quality-gate` passes Layer 1 mutation check
- **Per-module strategy** (lowest-hanging-fruit first, using actual kill rates from latest mutmut run):
  | # | Module | Current Kill Rate | Threshold | Gap to 100% | Priority |
  |---|--------|------------------|-----------|-------------|----------|
  | 1 | definitions | ~100% | 0.45 | ✅ Already met | Verify only |
  | 2 | diagnostics | ~93% | 0.28 | +7pp | Easy |
  | 3 | utils | ~89% | 0.89 | +11pp | Easy |
  | 4 | calculations | ~72% | 0.71 | +28pp | Medium |
  | 5 | vehicle_controller | ~55% | 0.55 | +45pp | Medium |
  | 6 | emhass_adapter | ~53% | 0.53 | +47pp | Medium |
  | 7 | presence_monitor | ~52% | 0.52 | +48pp | Medium |
  | 8 | yaml_trip_storage | ~51% | 0.50 | +49pp | Medium |
  | 9 | __init__ | ~52% | 0.51 | +48pp | Medium |
  | 10 | trip_manager | ~47% | 0.46 | +53pp | Hard |
  | 11 | dashboard | ~35% | 0.35 | +65pp | Hard |
  | 12 | services | ~38% | 0.38 | +62pp | Hard |
  | 13 | config_flow | ~31% | 0.31 | +69pp | Hard |
  | 14 | coordinator | ~38% | 0.37 | +62pp | Hard |
  | 15 | sensor | ~39% | 0.38 | +61pp | Hard |
  | 16 | panel | ~38% | 0.37 | +62pp | Hard |

  **Note**: `schedule_monitor` is excluded (deleted in Spec 1). After Spec 3 module splits, module names in `pyproject.toml` will change to reflect new package structure. Update mutation config accordingly.
- **Interface Contracts**: Tests may need significant rewrites. No source code API changes required.
- **Estimated Size**: **6.0-9.0 story points**
- **Dependencies**: None hard — can start in parallel with Spec 2 on low-hanging-fruit modules. Spec 3 refactoring makes modules more testable but doesn't block. After Spec 3, module names change — coordinate mutation config updates.

### Spec 6: Coverage Gap Closure — Zero `pragma: no cover`
- **Goal**: Eliminate all 273 `pragma: no cover` locations by making IO error paths testable via mocking.
- **Acceptance Criteria**:
  - AC-6.1: Zero `pragma: no cover` in any source file
  - AC-6.2: All IO error paths tested via `pytest.raises`, `unittest.mock.patch`, or equivalent
  - AC-6.3: `coverage report` shows 100% coverage with zero excluded lines
  - AC-6.4: `make test-cover` passes (`--cov-fail-under=100`)
  - AC-6.5: Mutation gate still passes (Spec 5 work overlaps)
- **Interface Contracts**: No API changes. Only test code additions.
- **Estimated Size**: **2.0-3.0 story points**
- **Dependencies**: Can run in parallel with Spec 5 (coverage tests often improve mutation scores)

### Spec 7: Lint, Format, and Type Cleanup
- **Goal**: Fix all remaining lint/format/type issues. Clean up debug logging.
- **Acceptance Criteria**:
  - AC-7.1: `ruff check` passes with zero errors
  - AC-7.2: `ruff format` passes with zero files needing reformat
  - AC-7.3: `pyright` passes with zero errors (resolve 16 sensor.py HA Entity override issues via `type: ignore` with justification comments, or protocol adoption)
  - AC-7.4: `pylint` passes with zero warnings
  - AC-7.5: E2E-DEBUG tagged logs gated behind environment variable (not removed — E2E tests depend on them). Pattern: `if os.environ.get("E2E_DEBUG"):`
  - AC-7.6: No unused imports anywhere
  - AC-7.7: 90+ DEBUG log lines reviewed — non-essential debug logs replaced with proper log levels
  - AC-7.8: Active TODOs in source code converted to GitHub issues or documented as accepted tech debt
- **Interface Contracts**: No API changes. Debug log gating is safe (environment variable, not used by any production logic).
- **Estimated Size**: **0.25 story points**
- **Dependencies**: After all refactoring is done (Specs 3-6)

### Spec 8: Security & CI Hardening
- **Goal**: Install and configure all Layer 4 security tools. Harden CI pipeline.
- **Acceptance Criteria**:
  - AC-8.1: `bandit` scans pass with zero HIGH findings (or documented acceptable risk)
  - AC-8.2: `gitleaks` scans find zero secrets
  - AC-8.3: `pip-audit` finds zero known vulnerabilities (or documented acceptable risk)
  - AC-8.4: CI workflow includes quality-gate, mutation, coverage, lint, and security scans
  - AC-8.5: `make security` target runs all Layer 4 tools
  - AC-8.6: Playwright CI workflow re-enabled — requires HA test instance in CI (Docker container or mock)
- **Interface Contracts**: CI-only changes. No code or API changes.
- **Estimated Size**: **0.5 story points**
- **Dependencies**: Spec 0 (tools installed first), Spec 7 (code must be clean for security scans)

## 5. Deterministic Gate Checkpoints

Each spec must pass ALL quality gate checks before the next spec begins:

| Checkpoint | Specs | Gate |
|------------|-------|------|
| **CP-0** | After Spec 0 | `make test` passes, all new tools installed, `make quality-gate` runs end-to-end |
| **CP-1** | After Spec 1 | `make test` passes (no regression from dead code removal), `ruff check` passes |
| **CP-2** | After Spec 2 | `make test` passes (test count ~1,830 after Spec 1 deletions), Layer 2 weak test count reduced < 200, no `assert True` |
| **CP-3** | After Spec 3 | `make test` passes, 0 SOLID violations, 0 circular cycles, 0 modules > 500 LOC, 0 classes > 20 methods |
| **CP-4** | After Spec 4 | `make test` passes, all functions <= 5 params, pyright passes |
| **CP-5** | After Spec 5 | `make mutation` passes, global kill rate >= 100%, all per-module thresholds met |
| **CP-6** | After Spec 6 | Coverage = 100% with 0 `pragma: no cover`, `make test-cover` passes |
| **CP-7** | After Spec 7 | `ruff check` passes, `ruff format` passes, pyright passes, pylint passes |
| **CP-8** | After Spec 8 | `make security` passes, CI green end-to-end, all workflow files active |

## 6. Phase Strategy & Rationale

### Phase 0: Tooling Foundation (Spec 0)
**What**: Install Layer 4 tools, fix mypy/pyright, add `make quality-gate`/`make mutation`/`make typecheck`, update CI.
**Why first**: Everything depends on tools being operational. If we refactor code first and break the tool chain, we can't verify correctness. mypy must be resolved early because it's a CI blocker.

### Phase 1: Dead Code & Artifact Elimination (Spec 1)
**What**: Delete `schedule_monitor.py`, remove backup files, update `.gitignore` for `*.py,cover` artifacts.
**Why second (or parallel with Phase 0)**: Dead code removal is zero-risk (confirmed 0 source imports). Can run in parallel with Spec 0. Reduces LOC count for all quality metrics. Must delete dependent test files too (`test_schedule_monitor.py`, update `test_coverage_edge_cases.py`).

### Phase 2: Test Architecture Reorganization (Spec 2)
**What**: Reorganize flat tests into unit/integration layers. Consolidate duplicates. Fix `assert True`.
**Why parallel with Phase 1**: Test reorganization is independent of dead code removal. Tests must be organized and reliable before any structural code changes (Spec 3). Also, consolidating coverage-driven tests into behavior-driven tests provides the safety net needed for aggressive refactoring.

### Phase 3: SOLID Refactoring — God Classes (Spec 3)
**What**: Split `EMHASSAdapter` (2,730 LOC), `TripManager` (2,503 LOC), `services.py` (1,635 LOC), `dashboard.py` (1,285 LOC), `vehicle_controller.py` (537 LOC), `calculations.py` (1,690 LOC). Eliminate circular imports.
**Why fourth**: Requires the strongest test safety net (Spec 2). Splitting god classes is high-risk — the test suite must be comprehensive and well-organized to catch regressions. This is the **critical path** (8-12 SP). Circular import fixes must come after module splits are decided.

### Phase 4: High-Arity & Parameter Refactoring (Spec 4)
**What**: Replace long parameter lists with dataclasses in all modules.
**Why after Phase 3**: Arity fixes are mechanical changes BUT the target functions live in modules that Spec 3 splits into packages. Running Spec 4 before Spec 3 means re-applying changes after the split. Running after ensures changes land in the correct final file locations. For modules NOT being split (config_flow, coordinator, sensor, etc.), arity fixes can proceed in parallel with Spec 3.

### Phase 5: Mutation Score Ramp (Spec 5) + Coverage Gap Closure (Spec 6)
**What**: Raise mutation kill rate 49% → 100%. Eliminate `pragma: no cover`.
**Why fifth/sixth**: These two specs are tightly coupled — better tests (mutation) often require covering IO paths (no cover). Doing both together ensures they reinforce each other. Can start in parallel with Spec 2 (low-hanging-fruit modules). Refactored modules (Spec 3) make them easier but don't block.

### Phase 6: Lint, Format, Type Cleanup (Spec 7)
**What**: Fix remaining ruff/pyright/pylint issues. Clean debug logs.
**Why seventh**: After all structural changes (Specs 3-6), format/lint/type issues will have changed. Doing this last avoids redoing formatting work.

### Phase 7: Security & CI Hardening (Spec 8)
**What**: Security tool gates, CI pipeline hardening.
**Why last**: Security scans operate on the final codebase. CI pipeline is the last thing to change — it validates everything. Re-enabling Playwright CI requires the test structure to be stable.

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| God class refactoring breaks behavior | HIGH | CP-3 gate with full test suite; each split validated before next |
| Mutation score tests break existing behavior | MEDIUM | Mutation tests should only kill mutated code; if tests are too permissive, tighten assertions |
| Test reorganization loses coverage | MEDIUM | Verify coverage stays 100% after reorganization (CP-2 + CP-3) |
| Circular import fixes change initialization order | MEDIUM | Test coordinator setup flow; verify HA startup works |
| `schedule_monitor.py` is actually used | LOW | Confirmed: grep returns 0 imports outside the file itself |
| Dataclass approach changes API surface | LOW | Maintain backward-compatible parameter order in new dataclass fields |
| HA Entity type override issues block pyright | MEDIUM | 16 pre-existing errors in `sensor.py`; use `type: ignore` with justification comments |

## 8. Estimated Total Effort

| Spec | Story Points | Priority |
|------|-------------|----------|
| Spec 0: Tooling Foundation | 0.5 | P0 — blocks everything |
| Spec 1: Dead Code & Artifacts | 0.25 | P0 — zero risk, independent |
| Spec 2: Test Architecture | 1.5-2.0 | P1 — safety net for refactoring, independent |
| Spec 3: SOLID Refactoring | 8.0-12.0 | P1 — highest impact, highest risk, critical path |
| Spec 4: High-Arity Fixes | 0.5 | P2 — mechanical, independent |
| Spec 5: Mutation Score Ramp | 6.0-9.0 | P1 — core quality target, can start in parallel |
| Spec 6: Coverage Gap Closure | 2.0-3.0 | P2 — coupled with Spec 5 |
| Spec 7: Lint/Format/Type | 0.25 | P3 — cleanup after all changes |
| Spec 8: Security & CI | 0.5 | P3 — final hardening |
| **Total** | **~19-28 story points** | |

## 9. Key Files Affected

### Source modules (18)
All modules in `custom_components/ev_trip_planner/` — affected files by spec:

| Spec | Files Changed |
|------|-------------|
| Spec 0 | `Makefile`, `pyproject.toml`, `.github/workflows/python-tests.yml`, `.gitignore` |
| Spec 1 | Delete: `schedule_monitor.py`. Remove: `*.cover` files, `frontend/panel.js.*`. Update: `pyproject.toml` mutation config |
| Spec 2 | Move/rename all `tests/test_*.py` → `tests/unit/`, `tests/integration/`. Update: `pyproject.toml` test paths |
| Spec 3 | Split: `emhass_adapter.py`, `trip_manager.py`, `services.py`, `dashboard.py`, `vehicle_controller.py`, `calculations.py`. Fix: `coordinator.py`, `sensor.py`, `presence_monitor.py`. Update: `services.yaml`, mutation config |
| Spec 4 | Modify: `calculations/`, `dashboard/`, `emhass/` (post-split packages) |
| Spec 5 | Add: new tests in `tests/unit/`, `tests/integration/` |
| Spec 6 | Modify: source files (remove `pragma: no cover`), add tests |
| Spec 7 | Modify: `sensor.py` (16 pyright errors), all source files (format/lint), E2E-DEBUG gating |
| Spec 8 | Add: `.github/workflows/security.yml`, modify `Makefile` |

## 10. Rollback Strategy

Each spec must be developed on its own branch with the following safety measures:

- **Branching**: `feat/tech-debt-spec-{N}` for each spec, merged to `feat/tech-debt-cleanup` only after checkpoint passes
- **Git tags**: `tech-debt-pre-spec-{N}` before starting each spec
- **Checkpoint commits**: Within Spec 3, commit after each module split (not just at the end)
- **Rollback procedure**: If a checkpoint fails and cannot be fixed, revert to the last passing tag
- **Quality gate snapshots**: Save gate results after each spec to `_bmad-output/quality-gate/` for comparison

## 11. Lessons Learned Template

After each spec is completed, document:

```markdown
### Spec {N}: {Name} — Lessons Learned
- **What went well**:
- **What went wrong**:
- **What surprised us**:
- **What we'd do differently**:
- **Impact on subsequent specs**:
```

This section is populated during implementation, not during planning.

## 12. Notes

- **POC shortcuts taken**: N/A — this is a production cleanup, not a feature. Every change is production-ready.
- **Production TODOs**: None — all changes are scoped to cleanup.
- **Spec 5 parallelization**: Mutation score improvement can be done in parallel across modules. Group modules by difficulty: easy (utils, definitions, diagnostics), medium (calculations, vehicle_controller, emhass_adapter), hard (config_flow, sensor, services, panel, dashboard).
- **Spec 6 and Spec 5 overlap**: Coverage gap closure often improves mutation scores. Coordinate these specs — some test additions serve both goals.
- **Spec 3 is the critical path**: This is the highest-risk, highest-effort spec. If it fails, the entire epic is blocked. Allocate the most experienced engineers to this spec.
- **Phase 2 SOLID tightening**: After this epic achieves ARN thresholds (500 LOC, 20 methods), a future epic will tighten to quality-gate.yaml thresholds (200 LOC, 7 methods).
- **mutation-testing skill**: Available as a global skill at `/home/malka/.roo/skills/mutation-testing/SKILL.md` — use for guidance when improving mutation scores in Spec 5.
- **Quality-gate workflow mapping**: The quality-gate skill at `.roo/skills/quality-gate/` uses step-file architecture. Spec-to-step mapping:
  - Spec 0 → `step-01-init.md` (initialize gate, install tools)
  - Spec 5 + Spec 6 → `step-02-layer1.md` (test execution, coverage, mutation)
  - Spec 2 + Spec 5 → `step-03-layer2.md` (test quality, weak tests, diversity)
  - Spec 7 → `step-03a-layer3a.md` (Tier A smoke test: ruff, pyright, SOLID)
  - Spec 3 → `step-04-layer3b.md` (Tier B BMAD Party Mode: SOLID Tier B, antipatterns)
  - All specs → `step-05-checkpoint.md` (checkpoint JSON generation)
  - Spec 8 → `step-06-layer4.md` (security and defense)
- **Quality-gate execution order**: L3A → L1 → L2 → L3B → L4. Fail-fast: if L3A smoke test fails, don't waste time on mutation testing (~15 min).
