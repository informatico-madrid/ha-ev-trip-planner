# Epic: Tech Debt Cleanup

## 1. Vision & Scope

Systematically eliminate all technical debt to achieve 100% SOLID compliance, zero Tier A/B antipatterns, 80% mutation kill rate, 100% test coverage, no `pragma: no cover`, zero warnings, clean architecture with separated tests, and all linters passing.

This epic touches all 18 source modules (~15,097 LOC), ~114 test files (~1,849 tests, including 10 TypeScript E2E), CI/CD, and Makefile infrastructure.

## 2. Quality Gate Targets

### Layer 1: Test Execution (currently PASS)
| Metric | Current | Target |
|--------|---------|--------|
| pytest | 1,848 passed, 0 failures | 1,848+ passed, 0 failures |
| Coverage | 100% | 100% (via `--cov-fail-under`) |
| Mutation modules passing | 17/17 | 17/17 |
| Mutation kill rate | 48-49% | 80% |
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
| Ruff errors | 1 (fixable) | 0 |
| mypy | BROKEN | Working or explicitly replaced by pyright |
| Circular import cycles | 3 | 0 |

### Layer 4: Security (currently 0 tools installed)
| Tool | Target |
|------|--------|
| bandit | Installed + CI gate |
| gitleaks | Installed + CI gate |
| pip-audit / safety | Installed + CI gate |
| semgrep | Installed (optional, no gate) |
| checkov | Installed (optional, no gate) |

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

### ARN-009: No unused imports or backup files
`.cover` files, `panel.js.bak/.old/.fixed` backups must be removed or moved to `_docs/`.

### ARN-010: All 17 modules meet per-module mutation thresholds
Each module's mutation kill rate must meet or exceed the target defined in `pyproject.toml`, with global floor of 80%.

## 4. Epic Decomposition

### Spec 0: Tooling Foundation
- **Goal**: Install missing tools, fix broken tooling, add Makefile targets, establish baseline metrics.
- **Acceptance Criteria**:
  - AC-0.1: `bandit` installed and `make security-bandit` target works
  - AC-0.2: `pip-audit` or `safety` installed and `make security-audit` target works
  - AC-0.3: `gitleaks` binary installed and `make security-gitleaks` target works
  - AC-0.4: `semgrep` installed
  - AC-0.5: `mypy` broken — replaced with `pyright` as primary type checker; `make typecheck` runs pyright
  - AC-0.6: `make quality-gate` target added (orchestrates layers 1-4)
  - AC-0.7: `make mutation` shortcut target added
  - AC-0.8: `make typecheck` replaces `make mypy` (pyright only, mypy skipped)
  - AC-0.9: All existing targets (`test`, `lint`, `format`, `e2e`, `check`) still work
  - AC-0.10: CI workflow updated to include quality-gate, mutation, and coverage gates
- **Interface Contracts**: Makefile targets must produce consistent exit codes (0 = pass, non-0 = fail) and machine-readable output for CI.
- **Estimated Size**: 2h (tool install) + 3h (Makefile/CI updates) = **0.5 story points**
- **Dependencies**: None (baseline, runs first)

### Spec 1: Dead Code & Artifact Elimination
- **Goal**: Remove all dead code, backup files, and stale artifacts. Reduce source LOC without changing behavior.
- **Acceptance Criteria**:
  - AC-1.1: `schedule_monitor.py` deleted (confirmed 0 source imports from any active code path)
  - AC-1.2: `tests/test_schedule_monitor.py` deleted (depends on schedule_monitor.py)
  - AC-1.3: `tests/test_coverage_edge_cases.py` updated to remove schedule_monitor import (line 529)
  - AC-1.4: All `*.py,cover` files (19 mutmut artifacts) added to `.gitignore`, NOT moved to `_docs/`
  - AC-1.5: `frontend/panel.js.bak`, `frontend/panel.js.old`, `frontend/panel.js.fixed` deleted
  - AC-1.6: `dashboard.py` remains (3 active importers: config_flow, services, __init__), but verified as god class target for Spec 3
  - AC-1.7: `vehicle_controller.py` remains (14 references across 4 files, IS wired), but verified as god class target for Spec 3
  - AC-1.8: `make test` still passes (test count drops by ~15-20 due to deleted test files, new count: ~1,830)
  - AC-1.9: No new import errors introduced
- **Interface Contracts**: No public APIs affected. `schedule_monitor.py` is never imported from production code.
- **Estimated Size**: 3-4h = **0.25 story points**
- **Dependencies**: None (can run in parallel with Spec 0)

### Spec 2: Test Architecture Reorganization
- **Goal**: Reorganize ~107 flat test files into unit/integration/E2E structure. Consolidate duplicate/weak tests. Eliminate `assert True`.
- **Acceptance Criteria**:
  - AC-2.1: Tests organized: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`
  - AC-2.2: 13 `test_trip_manager*.py` files consolidated into ≤ 3 focused test files
  - AC-2.3: 6 `test_config_flow*.py` files consolidated into ≤ 2 files
  - AC-2.4: Multiple `test_coverage*.py` files consolidated or replaced with behavior-driven tests
  - AC-2.5: 2 `assert True` violations fixed (replaced with real assertions or removed)
  - AC-2.6: Orphaned bug-finding tests (10 files) consolidated into behavior-driven regression tests
  - AC-2.7: `conftest.py` refactored: large fixture (~700 lines) split into module-scoped fixtures
  - AC-2.8: `make test` passes with >= 1,848 tests
  - AC-2.9: All pytest path configuration updated in `pyproject.toml`
- **Interface Contracts**: Test file paths change; `conftest.py` fixture signatures must remain compatible. Update `mutmut tests_dir` if paths change.
- **Estimated Size**: 12-20h = **1.5-2.0 story points**
- **Dependencies**: None (independent of Spec 0 and Spec 1; can run in parallel)

### Spec 3: SOLID Refactoring — God Classes
- **Goal**: Decompose god classes into focused modules. Eliminate all SOLID Tier A violations and 3 circular import cycles.
- **Acceptance Criteria**:
  - AC-3.0: `dashboard.py` (1,285 LOC) split into:
    - `dashboard/importer.py` — import_dashboard, DashboardImportResult
    - `dashboard/templates.py` — YAML/JS template management
  - AC-3.0b: `vehicle_controller.py` (537 LOC) split into:
    - `vehicle/strategy.py` — VehicleControlStrategy ABC + SwitchStrategy + ServiceStrategy
    - `vehicle/external.py` — ScriptStrategy + ExternalStrategy
    - `vehicle/controller.py` — VehicleController orchestrator
  - AC-3.0c: `calculations.py` (1,690 LOC) split into:
    - `calculations/windows.py` — charging window calculations
    - `calculations/power.py` — power profile generation
    - `calculations/deficit.py` — deficit propagation
  - AC-3.1: `emhass_adapter.py` (2,730 LOC, 41 methods) split into:
    - `emhass/index_manager.py` — assign/release/cleanup of deferrable load indices
    - `emhass/load_publisher.py` — async_publish_all, cache management
    - `emhass/error_handler.py` — notification and error recovery
  - AC-3.2: `trip_manager.py` (2,503 LOC, 49 methods) split into:
    - `trip/crud.py` — add/update/delete/list trips
    - `trip/soc_calculator.py` — SOC calculation logic (calcular_ventana_carga, etc.)
    - `trip/power_profile.py` — power profile generation
    - `trip/schedule_generator.py` — deferrables schedule generation
  - AC-3.3: `services.py` (1,635 LOC, 27 functions) split into:
    - `services/handlers.py` — service handler functions (grouped by domain)
    - `services/dashboard.py` — dashboard import helpers
    - `services/cleanup.py` — cleanup operations
  - AC-3.4: Circular import cycles eliminated:
    - `coordinator -> trip_manager -> sensor -> coordinator` → `from __future__ import annotations` in coordinator.py
    - `trip_manager -> vehicle_controller -> presence_monitor -> trip_manager` → TYPE_CHECKING imports
    - `trip_manager -> vehicle_controller -> trip_manager` → string type annotations
  - AC-3.5: All 18 modules <= 500 LOC
  - AC-3.6: All classes <= 20 public methods
  - AC-3.7: `make test` passes with >= 1,848 tests
  - AC-3.8: No new pyright errors introduced
- **Interface Contracts**: Public API surface of `TripManager` and `EMHASSAdapter` must remain identical. Refactored modules expose the same methods/signatures. Update imports in all consumers.
- **Estimated Size**: 80-120h = **8.0-12.0 story points**
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
- **Estimated Size**: 8-12h = **0.5 story points**
- **Dependencies**: None (mechanical change; can run in parallel with Spec 2 or after Spec 3 for cleaner modules)

### Spec 5: Mutation Score Ramp (48% → 80%)
- **Goal**: Incrementally raise mutation kill rate from ~49% to 80% across all 17 modules.
- **Acceptance Criteria**:
  - AC-5.1: All 17 modules meet or exceed target kill rate from pyproject.toml
  - AC-5.2: Global kill rate >= 80%
  - AC-5.3: Per-module status all changed from `"in_progress"` to `"passing"`
  - AC-5.4: `make mutation` passes
  - AC-5.5: `make quality-gate` passes Layer 1 mutation check
- **Per-module strategy** (lowest-hanging-fruit first):
  1. `definitions` (100% → 80%) — already strong, verify
  2. `diagnostics` (93% → 80%) — already strong, verify
  3. `utils` (89% → 80%) — already strong, verify
  4. `calculations` (72% → 80%) — +8pp needed
  5. `vehicle_controller` (55% → 80%) — +25pp needed
  6. `emhass_adapter` (53% → 80%) — +27pp needed
  7. `presence_monitor` (52% → 80%) — +28pp needed
  8. `yaml_trip_storage` (51% → 80%) — +29pp needed
  9. `schedule_monitor` (50% → 80%) — +30pp (delete in Spec 1, skip this module)
  10. `__init__` (52% → 80%) — +28pp needed
  11. `trip_manager` (47% → 80%) — +33pp needed
  12. `dashboard` (35% → 80%) — +45pp needed
  13. `services` (38% → 80%) — +42pp needed
  14. `config_flow` (31% → 80%) — +49pp needed
  15. `coordinator` (38% → 80%) — +42pp needed
  16. `sensor` (39% → 80%) — +41pp needed
  17. `panel` (38% → 80%) — +42pp needed
- **Interface Contracts**: Tests may need significant rewrites. No source code API changes required.
- **Estimated Size**: 60-90h = **6.0-9.0 story points**
- **Dependencies**: None hard — can start in parallel with Spec 2 on low-hanging-fruit modules. Spec 3 refactoring makes modules more testable but doesn't block.

### Spec 6: Coverage Gap Closure — Zero `pragma: no cover`
- **Goal**: Eliminate all 273 `pragma: no cover` locations by making IO error paths testable via mocking.
- **Acceptance Criteria**:
  - AC-6.1: Zero `pragma: no cover` in any source file
  - AC-6.2: All IO error paths tested via `pytest.raises`, `unittest.mock.patch`, or equivalent
  - AC-6.3: `coverage report` shows 100% coverage with zero excluded lines
  - AC-6.4: `make test-cover` passes (`--cov-fail-under=100`)
  - AC-6.5: Mutation gate still passes (Spec 5 work overlaps)
- **Interface Contracts**: No API changes. Only test code additions.
- **Estimated Size**: 24-36h = **2.0-3.0 story points**
- **Dependencies**: Can run in parallel with Spec 5 (coverage tests often improve mutation scores)

### Spec 7: Lint, Format, and Type Cleanup
- **Goal**: Fix all remaining lint/format/type issues. Clean up debug logging.
- **Acceptance Criteria**:
  - AC-7.1: `ruff check` passes with zero errors
  - AC-7.2: `ruff format` passes with zero files needing reformat
  - AC-7.3: `pyright` passes with zero errors (resolve 16 sensor.py HA Entity override issues via `type: ignore` or protocol adoption)
  - AC-7.4: `pylint` passes with zero warnings
  - AC-7.5: No E2E-DEBUG tagged logs remain in production code (remove or gate behind feature flag)
  - AC-7.6: No unused imports anywhere
  - AC-7.7: 90+ DEBUG log lines reviewed — non-essential debug logs replaced with proper log levels
- **Interface Contracts**: No API changes. Debug log removal is safe (DEBUG level, not used by any production logic).
- **Estimated Size**: 4-6h = **0.25 story points**
- **Dependencies**: After all refactoring is done (Specs 3-6)

### Spec 8: Security & CI Hardening
- **Goal**: Install and configure all Layer 4 security tools. Harden CI pipeline.
- **Acceptance Criteria**:
  - AC-8.1: `bandit` scans pass with zero HIGH findings (or documented acceptable risk)
  - AC-8.2: `gitleaks` scans find zero secrets
  - AC-8.3: `pip-audit` finds zero known vulnerabilities (or documented acceptable risk)
  - AC-8.4: CI workflow includes quality-gate, mutation, coverage, lint, and security scans
  - AC-8.5: `make security` target runs all Layer 4 tools
  - AC-8.6: Playwright CI workflow re-enabled (was `.yml.disabled`)
- **Interface Contracts**: CI-only changes. No code or API changes.
- **Estimated Size**: 4-6h = **0.5 story points**
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
| **CP-5** | After Spec 5 | `make mutation` passes, global kill rate >= 80%, all per-module thresholds met |
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
**Why fifth (or parallel with Phase 3)**: Arity fixes are mechanical changes. Can run in parallel with Spec 2 or after Spec 3. After god classes are split, modules are smaller and functions better scoped.

### Phase 5: Mutation Score Ramp (Spec 5) + Coverage Gap Closure (Spec 6)
**What**: Raise mutation kill rate 49% → 80%. Eliminate `pragma: no cover`.
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
| Spec 0 | `Makefile`, `pyproject.toml`, `.github/workflows/python-tests.yml` |
| Spec 1 | Delete: `schedule_monitor.py`. Move: `*.cover` files, `frontend/panel.js.*` |
| Spec 2 | Move/rename all `tests/test_*.py` → `tests/unit/`, `tests/integration/` |
| Spec 3 | Split: `emhass_adapter.py`, `trip_manager.py`, `services.py`. Fix: `coordinator.py`, `sensor.py`, `presence_monitor.py`, `vehicle_controller.py` |
| Spec 4 | Modify: `calculations.py`, `dashboard.py`, `emhass_adapter.py` |
| Spec 5 | Add: new tests in `tests/unit/`, `tests/integration/` |
| Spec 6 | Modify: source files (remove `pragma: no cover`), add tests |
| Spec 7 | Modify: `sensor.py` (16 pyright errors), all source files (format/lint) |
| Spec 8 | Add: `.github/workflows/security.yml`, modify `Makefile` |

## 10. Notes

- **POC shortcuts taken**: N/A — this is a production cleanup, not a feature. Every change is production-ready.
- **Production TODOs**: None — all changes are scoped to cleanup.
- **Spec 5 parallelization**: Mutation score improvement can be done in parallel across modules. Group modules by difficulty: easy (utils, definitions, diagnostics), medium (calculations, vehicle_controller, emhass_adapter), hard (config_flow, sensor, services, panel, dashboard).
- **Spec 6 and Spec 5 overlap**: Coverage gap closure often improves mutation scores. Coordinate these specs — some test additions serve both goals.
- **Spec 3 is the critical path**: This is the highest-risk, highest-effort spec. If it fails, the entire epic is blocked. Allocate the most experienced engineers to this spec.
