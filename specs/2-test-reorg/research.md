---
spec: 2-test-reorg
phase: research
created: 2026-05-09
updated: 2026-05-09
reviewed: adversarial + 4 parallel agents
---

# Research: 2-test-reorg — Test Architecture Reorganization

## Executive Summary

The test suite has **1,821 Python tests across 104 test files** (60,220 LOC) plus **10 TypeScript E2E tests** (2,587 LOC) in two Playwright suites. All Python tests live in a single flat `tests/` directory with no layer separation. The epic's ARN-008 mandates `tests/unit/`, `tests/integration/`, `tests/e2e/` separation with `test_{module}_{aspect}.py` naming. Currently zero tests follow this convention. The reorganization is **HIGH risk** (not medium) due to `fail_under = 100` — any single missed import drops coverage below 100% and fails the entire quality gate.

**Adversarial review** found 4 CRITICAL issues in the initial research: wrong test count (1,821 vs 1,815), underestimated risk from 100% coverage gate, phantom integration criteria (`setup_mock_ev_config_entry` is unused), and missing pytest marker registration. 47 test files (45%) lack clear single-module mapping, making the initial 14-subdirectory strategy unimplementable as-is.

**Recommendation**: Phased commit strategy — minimum viable reorganization first (flat `tests/unit/` with all 104 files), then incremental improvements (subdirectories, renaming, fixture splitting, helpers extraction). Each phase verified against `fail_under = 100`.

## Current Architecture Assessment

### Directory Structure

```
tests/
  conftest.py                          (702 LOC, 23 fixtures)
  __init__.py                          (198 LOC: constants, fakes, factories)
  setup_entry.py                       (manual HA entry setup utility)
  panel.test.js                        (standalone Jest panel test, NOT Playwright)
  test_*.py                            (104 files, flat, no subdirs)
  fixtures/
    dashboards/crud_dashboard.yaml
    trips/{punctual,recurring}_trips.json
    vehicles/{nissan_leaf,tesla_model3}.json
  e2e/                                 (8 .spec.ts files, Playwright, port 8123)
  e2e-dynamic-soc/                     (2 .spec.ts + 1 helper, Playwright, port 8123)
  logs/
tests_excluded_from_mutmut/            (2 files)
```

### Test Inventory (Verified)

| Category | Count | Details |
|----------|-------|---------|
| Python test files | 104 | All flat in `tests/` |
| Total Python tests | 1,821 | `pytest --co -q` verified |
| Python test LOC | 60,220 | In `tests/test_*.py` |
| conftest.py | 702 LOC | 23 fixtures (not 16) |
| `__init__.py` shared | 198 LOC | Constants, FakeTripStorage, FakeEMHASSPublisher, factories |
| E2E TypeScript tests | 10 | 8 in `tests/e2e/`, 2 in `tests/e2e-dynamic-soc/` |
| E2E LOC | 2,587 | `.spec.ts` files |
| Excluded from mutmut | 2 | `test_timezone_utc_vs_local_bug.py`, `test_vehicle_controller_event.py` |

### Source Module -> Test File Mapping

| Source Module | LOC | Test Files | Primary Test Pattern |
|---------------|-----|------------|---------------------|
| `trip_manager.py` | 2,503 | 18 files | `test_trip_manager*.py` + `test_trip_*.py` |
| `emhass_adapter.py` | 2,733 | 11 files | `test_emhass_*.py` |
| `calculations.py` | 1,690 | 12 files | `test_calculations.py`, `test_*_bug.py`, `test_charging*.py` |
| `config_flow.py` | 1,038 | 6 files | `test_config_flow*.py` |
| `dashboard.py` | 1,285 | 5 files | `test_dashboard*.py` |
| `definitions.py` | 97 | 5 files | `test_definitions.py`, `test_sensor_*.py`, `test_coordinator_entity.py` |
| `__init__.py` | 227 | 3 files | `test_init.py`, `test_coverage_100_percent.py`, `test_services_core.py` |
| `sensor.py` | 1,041 | 2 files | `test_sensor_*.py` |
| `coordinator.py` | 320 | 2 files | `test_coordinator.py`, `test_t32_and_p11_tdd.py` |
| `const.py` | 105 | 24 files | Cross-cutting — many files import from const |
| `yaml_trip_storage.py` | 65 | 1 file | `test_yaml_trip_storage.py` |
| `vehicle_controller.py` | 537 | 1 file | `test_vehicle_controller.py` |
| `utils.py` | 353 | 1 file | `test_utils.py` |
| `services.py` | 1,635 | 1 file | `test_trip_create_branches.py` |
| `presence_monitor.py` | 806 | 1 file | `test_vehicle_controller_event.py` |
| `diagnostics.py` | 82 | 1 file | `test_diagnostics.py` |
| **Unmapped (cross-cutting)** | - | **47 files** | No obvious single-module mapping |

### Naming Convention Violations

**45+ files** with non-standard suffixes (not 28):
- `_bug`: 13 files (regression tests)
- `_coverage/_cover/_missing`: 26 files (coverage-driven tests)
- `_tdd`: 3 files (TDD phase indicators)
- `_milestone`: 3 files (milestone markers)
- `_red`: 1 file (TDD red phase)
- `_fix/_branches/_edge/_more/_line*`: ~10 files

### Test Classification Analysis

**CRITICAL FINDING**: The initial research claimed `setup_mock_ev_config_entry` factory usage as the integration test criteria. This function is **NOT used by any test file** (`grep -rl` returns 0 results). The integration classification must be re-derived.

Actual classification signals (verified by multiple counting methods, 2026-05-09):
- **11 test files** use `MockConfigEntry` (12 including `__init__.py`)
- **30 test files** import from `homeassistant` via `from homeassistant` / `import homeassistant`
- **41 test files** reference `homeassistant` in any way (imports, type annotations, comments)
- **43 files** reference `homeassistant` including conftest.py + `__init__.py`
- **17 test files** import from 3+ source modules (cross-cutting)
- **28 test files** define their own `mock_hass` function (52 files reference `mock_hass` in any way)
- **4 test files** import from `tests.__init__` directly (low chain risk)

Classification framework (Meszaros/Fowler):

| Layer | Criteria | Estimated Files |
|-------|----------|----------------|
| **Unit** | Imports only from `custom_components.*` and stdlib. No `homeassistant` imports. Uses Fakes (FakeTripStorage, FakeEMHASSPublisher). | ~63 files (104 - 41 with HA refs) |
| **Integration** | Imports from `homeassistant.*`. Uses mocked `hass`, `MockConfigEntry`, entity registry mocks. Tests interaction between code and HA framework. | ~30 files (those with explicit HA imports) |
| **Cross-cutting** | Imports from 3+ source modules. Tests multi-module interactions. | ~17 files (overlap with above) |

**Recommendation**: Write a classification script that detects integration patterns (MockConfigEntry lifecycle, `hass.config_entries`, `async_setup_entry` imports, 3+ module imports) and auto-classifies. Manual review for edge cases.

## Pain Points Identified

### P1: Flat Structure — No Layer Separation
All 104 Python test files sit in `tests/` with zero subdirectory organization. ARN-008 requires `tests/unit/`, `tests/integration/`, `tests/e2e/`. Currently impossible to run only unit or only integration tests.

### P2: Naming Chaos
45+ files use non-standard suffixes. File names describe HOW they were written (TDD, coverage-driven) not WHAT they test. Numeric codes (`test_t32_and_p11_tdd.py`) are opaque.

### P3: Fixture Duplication & Quality Issues
- **28 test files** define their own `mock_hass` function (52 files reference `mock_hass` in any way)
- **11 test files** use `MockConfigEntry`
- **25+ MagicMock instances** created without `spec=` parameter (duck typing violation)
- **540 patch() calls** across test files (string-path coupling)
- conftest.py is 702 LOC with 23 fixtures — needs splitting
- Hardcoded magic numbers in test data (latitude 40.0, longitude -3.0, battery 60.0)

### P4: No Unit vs Integration Distinction
41 out of 104 test files reference `homeassistant` (30 with explicit imports). 63 files import only from `custom_components.*` and stdlib — these are pure unit test candidates. However, they are mixed with integration-weight tests in the same flat directory, making selective test runs impossible.

### P5: Coverage-Driven Test Sprawl
26+ files are named for coverage targets. These tend to be low-quality tests written to hit lines rather than verify behavior. Should be reviewed for consolidation or deletion.

### P6: Config Coupling (HIGH RISK due to fail_under=100)
- `pyproject.toml`: `fail_under = 100` — ANY import break drops coverage below threshold
- `pyproject.toml [tool.mutmut]`: `tests_dir = ["tests/"]`
- Makefile: 6 targets with `--ignore=tests/e2e/`
- `tests/__init__.py`: Only 4 test files import from it directly — low chain risk, but still needs care
- CI: `make quality-gate-ci` calls Makefile targets — indirect dependency

### P7: Missing Test Design Patterns
- No pytest markers registered (`unit`, `integration`, `slow`)
- No `--import-mode=importlib` for subdirectory test structure
- Only 13 parametrized tests out of 1,821 (consolidation opportunity)
- `tests/__init__.py` mixes constants, fakes, and factories (should be separated)
- `panel.test.js` uses Jest (not Playwright) — should not be moved to `e2e/`

## ARN-008 Compliance Gap

| ARN-008 Requirement | Current State | Gap |
|---------------------|---------------|-----|
| `tests/unit/` directory | Does not exist | Must create |
| `tests/integration/` directory | Does not exist | Must create |
| `tests/e2e/` directory | Exists (TypeScript only) | OK |
| `test_{module}_{aspect}.py` naming | 0 files follow this | Must rename ~104 files |
| Shared fixtures in `tests/conftest.py` | Exists but bloated (702 LOC, 23 fixtures) | Needs splitting |
| `tests/fixtures/` | Exists (3 subdirs) | OK |
| `tests/helpers/` | Does not exist | Must create |
| `tests_excluded_from_mutmut/` evaluated | 2 files exist | Evaluate: defer to Spec 5 |

## Test Design Patterns & Anti-Patterns (External Research)

### Test Double Taxonomy (Meszaros/Fowler)

| Double | Purpose | Python Implementation | When to Use |
|--------|---------|----------------------|-------------|
| **Dummy** | Fill parameter lists | `MagicMock()` without spec | Unused parameters |
| **Stub** | Canned responses | `MagicMock(return_value=X)` | "When I call X, return Y" |
| **Spy** | Stub + records calls | `MagicMock(wraps=real_obj)` | Verify interaction happened |
| **Mock** | Behavior verification | `MagicMock()` + `.assert_called_with()` | Verify specific behavior |
| **Fake** | Working implementation | Hand-written class | Complex collaborator (FakeTripStorage) |

### Anti-Patterns Detected in This Codebase

| Anti-Pattern | Evidence | Severity | Files |
|--------------|----------|----------|-------|
| Duplicate `mock_hass` | 28 files define own mock_hass (52 reference it) | HIGH | 28/104 |
| MagicMock without `spec=` | 25+ instances | HIGH | 25+ |
| Coverage-driven naming | 26 files named `_coverage/_cover/_missing` | MEDIUM | 26/104 |
| No test markers | Zero `@pytest.mark.unit/integration` | HIGH | All 104 |
| Monolithic conftest.py | 702 LOC, 23 fixtures | MEDIUM | 1 |
| Mixed concerns in `__init__.py` | Constants + fakes + factories | MEDIUM | 1 |
| Hardcoded magic numbers | Latitude, longitude, battery capacity | LOW | 15+ |
| Over-patching | 540 `patch()` calls via string path | MEDIUM | Many |

### Recommended Patterns

1. **Factory fixtures** for commonly doubled types (`hass`, `store`, `trip_manager`) in per-directory `conftest.py`
2. **`patch`** only at framework boundaries — never to replace own code's internals
3. **Hand-crafted Fakes** (FakeTripStorage, FakeEMHASSPublisher) are CORRECT — keep them
4. **`spec=`** on all MagicMock instances to catch interface drift
5. **`--import-mode=importlib`** for subdirectory test structure (avoids sys.path issues)
6. **Strict markers**: Register `unit`, `integration`, `slow` in `pyproject.toml`

## Modern Testing Standards & Tools (Web Research + Codebase Analysis)

### Industry-Standard Tools Assessment

| Tool | Purpose | Relevance | Status | Rationale |
|------|---------|-----------|--------|-----------|
| **pytest strict mode** | `strict = true` (pytest 9.0+) enables strict_markers, strict_config, etc. | HIGH | Not configured | Prevents silent marker typos, unknown config options, unregistered markers. Must add. |
| **flake8-pytest-style** | Lints pytest code for common mistakes | HIGH | Not installed | Catches incorrect fixture usage, naming violations, marker misuse. Recommended by pytest docs. |
| **--import-mode=importlib** | Modern pytest import mode for subdirectory tests | HIGH | Not configured | Eliminates sys.path issues with same-named test files in subdirectories. Required for subdirectory structure. |
| **time-machine** | Fast time mocking (C-level, not module scanning) | HIGH | Not installed | Replaces fragile manual datetime mocking. 100x faster than freezegun. Project has time-sensitive tests (tz, recurring trips). |
| **Hypothesis** | Property-based testing for calculation-heavy code | MEDIUM | Not installed | Excellent for `calculations.py` (charging windows, SOC). Generates edge cases automatically. Only for tests that use it — no impact on others. |
| **Syrupy** | Snapshot testing (zero-dependency pytest plugin) | LOW | Not installed | Could validate dashboard YAML output. But project has few serialization-heavy tests. Defer to future evaluation. |
| **pytest-xdist** | Parallel test execution | Installed | Already in Makefile | `-n auto` for parallel runs. Works with reorganized structure. |
| **pytest-randomly** | Random test ordering | Installed | Already in Makefile | Catches hidden inter-test dependencies. Critical after reorganization to prove independence. |

### Production-Test Harmony Analysis

**Source module testability audit:**

| Module | LOC | Testability | Issue | Fix |
|--------|-----|-------------|-------|-----|
| `trip_manager.py` | 2,503 | LOW | Hard-coded `self.hass`, no DI, direct `hass.states.async_set()` side effects | Spec 3 splits into package. Tests should target public API, not internals. |
| `emhass_adapter.py` | 2,733 | LOW | `hass.data.get()` global state, direct `hass.services.async_call()` | Same — Spec 3 split. Use FakeEMHASSPublisher for unit tests. |
| `calculations.py` | 1,690 | MEDIUM | Pure functions but some high-arity (8-9 params) | Excellent unit test candidate. Hypothesis for edge cases. |
| `vehicle_controller.py` | 537 | HIGH | ABC strategy pattern, `HomeAssistantWrapper` DI | Good testability. Can inject fake wrapper. |
| `utils.py` | 353 | HIGH | Pure functions, no HA dependencies | Perfect unit testing. No mocks needed. |
| `config_flow.py` | 1,038 | LOW | ConfigEntry lifecycle, HA framework integration | Integration test territory. |
| `dashboard.py` | 1,285 | MEDIUM | YAML templating, side effects | Split in Spec 3. Template tests are unit, import tests are integration. |

**Async testing patterns:**
- 1,091 test functions use `@pytest.mark.asyncio` (rely on `asyncio_mode = auto`)
- conftest.py has **zero async fixtures** — all fixtures are sync
- **Recommendation**: Async methods MUST use `AsyncMock` with `spec=`, never `MagicMock`
- **Recommendation**: Add async factory fixtures where async setup is needed

**Test double selection per layer:**

| Test Layer | For `hass` | For `Store` | For `ConfigEntry` | For business collaborators |
|------------|-----------|-------------|-------------------|---------------------------|
| **Unit** | Not needed (no HA imports) | `FakeTripStorage` (hand-crafted Fake) | Not needed | `MagicMock(spec=RealClass)` or Fakes |
| **Integration** | `MagicMock(spec=HomeAssistant)` with attribute mocks | `MagicMock(spec=Store)` | `MagicMock(spec=ConfigEntry)` | Real implementations with mocked HA layer |

**Future-proofing for Spec 3 (god class splits):**

The key principle: **test by interface, not by implementation**. When `trip_manager.py` splits into `trip/__init__.py` + `trip/crud.py` + `trip/soc_calculator.py`:
1. Tests that call `TripManager.async_add_trip()` should continue working (public API unchanged)
2. Tests that test internal calculations should target the new sub-module directly
3. The reorganization should place tests in per-module directories that mirror the future package structure

### Recommended pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/integration"]
asyncio_mode = "auto"
import_mode = "importlib"
strict = true
markers = [
    "unit: pure Python logic, no HA framework",
    "integration: tests with HA framework types",
    "slow: tests taking >1s",
]
addopts = [
    "--strict-markers",
    "--strict-config",
]
```

### Recommended Test Quality Tools

1. **flake8-pytest-style** — Lint pytest patterns (fixture naming, marker usage, assertion patterns)
2. **time-machine** — Replace manual datetime mocking in conftest.py (`mock_datetime_2026_05_04_monday_0800_utc` → `@time_machine.travel()`)
3. **Hypothesis** — For `calculations.py` charging window edge cases (only where beneficial)
4. **pytest-randomly** — Already installed, critical post-reorganization to prove test independence

### Anti-Patterns to Eliminate During Reorganization

| Anti-Pattern | Current Count | Fix |
|--------------|--------------|-----|
| MagicMock without `spec=` | 25+ instances | Add `spec=` parameter to all mocks |
| Inline `mock_hass` definitions | 28 files | Consolidate into conftest.py hierarchy |
| `MagicMock` for async methods | Unknown | Replace with `AsyncMock` + `spec=` |
| Hardcoded test data (magic numbers) | 15+ instances | Extract to named constants or fixtures |
| Coverage-driven test names | 26 files | Rename to behavior-based names |
| No test markers | All 104 files | Add `@pytest.mark.unit` / `@pytest.mark.integration` |
| Monolithic conftest.py | 702 LOC, 23 fixtures | Split into root + unit + integration |

## E2E Architecture

### Two Separate Playwright Suites

| Suite | Directory | Files | Config | HA Config | Port | Command |
|-------|-----------|-------|--------|-----------|------|---------|
| Main | `tests/e2e/` | 8 .spec.ts | `playwright.config.ts` (project: main) | `/tmp/ha-e2e-config/` | 8123 | `make e2e` |
| SOC | `tests/e2e-dynamic-soc/` | 2 .spec.ts + 1 helper | `playwright.config.ts` (project: soc) | `/tmp/ha-e2e-soc-config/` | 8123 | `make e2e-soc` |

**E2E tests are NOT affected** by Python test reorganization. They are TypeScript, not Python. They already have their own directory structure. No changes needed.

## Mutation Testing Integration

### Current Configuration

```toml
[tool.mutmut]
paths_to_mutate = ["custom_components/ev_trip_planner"]
runner = "pytest"
tests_dir = ["tests/"]
timeout = 600
global_kill_threshold = 0.48
```

### 17 Modules Tracked (kill rates from pyproject.toml)

- 8 passing (diagnostics, definitions, utils, calculations, presence_monitor, emhass_adapter, vehicle_controller, yaml_trip_storage)
- 9 in_progress (sensor, trip_manager, config_flow, coordinator, dashboard, services, panel, __init__, one more)

### Impact of Reorganization

- **mutmut WILL break** if `tests_dir` is not updated when files move
- Required change: `tests_dir = ["tests/unit/", "tests/integration/"]`
- E2E tests should be EXCLUDED from mutmut (TypeScript, slow, system-level)
- Reorganization does NOT affect mutation scores (scores depend on test quality, not file location)
- `tests_excluded_from_mutmut/` migration should be deferred to Spec 5

### Spec 5 Timing (Epic Planning)

**Mutation testing is planned for Spec 5**, NOT Spec 2. Spec 2 must:
1. Update `tests_dir` configuration when paths change
2. Verify mutmut still discovers all test files after reorganization
3. Preserve test quality (don't weaken assertions during reorganization)
4. NOT attempt to improve mutation scores (that's Spec 5's job)

## Coverage Configuration

```toml
[tool.coverage.run]
source = ["custom_components/ev_trip_planner"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 100
exclude_lines = [
    "pragma: no cover",  # 118 instances in source code
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstract",
]
```

**Coverage is NOT affected** by test path changes (source path stays the same, tests are omitted). The 118 `pragma: no cover` lines are Spec 6's concern.

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Technical Viability | **High** | Mechanical file moves + import updates |
| Effort Estimate | **L** (Large) | 104 files to move/rename, conftest to split, config to update |
| Risk Level | **HIGH** (not medium) | `fail_under = 100` means ANY import break fails the gate |
| Reversibility | **High** | Git tracks moves, easy to revert |

### Risk: Spec 3 Ordering
Spec 3 (SOLID Refactoring) will split source modules. Spec 2 must establish test structure FIRST. But Spec 2 should NOT align test names with source modules that don't exist yet — use current module names. Spec 3 updates naming post-split.

### Risk: 100% Coverage Gate
Moving 104 files with `fail_under = 100` is the highest-risk aspect. **Phased commit strategy required** — each commit must pass 100% before the next batch.

### Risk: `__init__.py` Import Chain
Only 4 test files import from `tests.__init__` (low chain risk). However, conftest.py and `__init__.py` contain shared fakes/factories that many tests use indirectly. Extracting to `helpers/` is still recommended but lower priority than initially assessed.

## Recommended Reorganization Strategy (Phased)

### Phase 1: Minimum Viable Reorganization (1 commit)

Create `tests/unit/` (FLAT, no subdirectories). Move all 104 test files there. Update `testpaths`, `--ignore` flags, mutmut `tests_dir`. Verify 1,821 tests pass at 100% coverage.

**Rationale**: This achieves ARN-008 compliance with minimal risk. All subsequent improvements are incremental.

### Phase 2: Integration Layer Separation (1 commit)

Write classification script. Identify ~30 integration-weight tests (those with `homeassistant` imports). Move them to `tests/integration/`. Register pytest markers (`unit`, `integration`, `slow`) in `pyproject.toml`. Apply markers. Verify.

Rename all 104 files to `test_{module}_{aspect}.py` convention. Consolidate coverage-driven files where safe. Verify.

### Phase 4: Fixture Consolidation (1 commit)

Split conftest.py (root -> unit -> integration). Remove duplicate mock_hass definitions (28 files). Add `spec=` to all MagicMock instances. Extract helpers/ from `__init__.py`. Verify.

### Phase 5: Module Subdirectories (optional, 1 commit)

Create 14 module subdirectories under `tests/unit/`. Move files into per-module directories. Add per-module `conftest.py` files. Verify.

**Each phase is a separate commit. Each commit must pass `fail_under = 100`. If any phase fails, revert and fix before proceeding.**

## Configuration Updates Required

| File | Current | Target |
|------|---------|--------|
| `pyproject.toml testpaths` | `["tests"]` | `["tests/unit", "tests/integration"]` |
| `pyproject.toml tests_dir` | `["tests/"]` | `["tests/unit/", "tests/integration/"]` |
| `pyproject.toml markers` | (none) | `["unit: ...", "integration: ...", "slow: ..."]` |
| `pyproject.toml import_mode` | (default) | `importlib` |
| Makefile 6 targets | `pytest tests --ignore=tests/e2e/` | `pytest tests/unit tests/integration` |
| `.pre-commit-config.yaml` | `exclude: tests/` for bandit | Verify recursive scanning works |
| CI workflow | `make quality-gate-ci` | No change (uses Makefile targets) |

## Verification Protocol

After each phase:

1. `pytest --co -q > after.txt` — same test count (1,821)
2. `pytest` — all tests pass
3. `pytest --cov --cov-fail-under=100` — coverage maintained
4. `make test` — Makefile target works
5. `make e2e` + `make e2e-soc` — E2E unaffected
6. `mutmut run --list` — mutmut discovers tests correctly

## Related Specs

| Spec | Relationship | Impact |
|------|-------------|--------|
| `spec1-dead-code` | Predecessor (completed) | Tests for deleted schedule_monitor already removed. Baseline: 1,821 tests |
| Epic Spec 3 (SOLID Refactoring) | **Sequential dependency** | Spec 3 splits source modules AFTER Spec 2 establishes test structure |
| Epic Spec 5 (Mutation Ramp) | **Sequential** | Spec 5 improves mutation scores using new test structure. Spec 2 must update `tests_dir` |
| Epic Spec 6 (Coverage Gap) | **Sequential** | Spec 6 eliminates 118 `pragma: no cover` lines. Spec 2 must maintain 100% coverage |
| Epic Spec 7 (Lint/Format/Type) | **After** | Spec 7 cleans lint/format on files in new locations |

## Open Questions

1. **Should all 26 coverage-named files be consolidated?** Recommend deferring consolidation to Spec 5. Spec 2 should only rename them.
2. **Module subdirectories vs flat unit/?** Recommend flat first, subdirectories as optional Phase 5. 47 files lack clear mapping.
3. **Integration test boundary**: Need automated classification script. 11 files use `MockConfigEntry`; 30 files have `from homeassistant` imports.
4. **`tests_excluded_from_mutmut/`**: Defer to Spec 5 (Mutation Ramp) where it belongs thematically.
5. **`panel.test.js`**: Keep in `tests/` root. It uses Jest, not Playwright — should NOT move to `e2e/`.
6. **Batch size for file moves**: Recommend all-in-one move (single commit) with immediate verification, not incremental per-file moves.
7. **`__init__.py` extraction timing**: MUST be a separate commit from file moves. Chain dependency risk is too high.
8. **`--import-mode=importlib`**: Required for subdirectory structure with same-named files. Must add in Phase 1.

## Sources

- `tests/` directory scan (104 Python files, 10 TypeScript files)
- `tests/conftest.py` (702 LOC, 23 fixtures)
- `tests/__init__.py` (198 LOC: shared fakes, factories, constants)
- `pyproject.toml` (pytest, mutmut, coverage config)
- `Makefile` (6-layer quality gate, test targets)
- `playwright.config.ts` (E2E config)
- `specs/_epics/tech-debt-cleanup/epic.md` (ARN-008 requirements, 8 specs)
- `.github/workflows/python-tests.yml` (CI pipeline)
- `.pre-commit-config.yaml` (hooks)
- Martin Fowler: "Mocks Aren't Stubs"
- Meszaros: "xUnit Test Patterns" (test double taxonomy)
- Freeman & Pryce: "Growing Object-Oriented Software, Guided by Tests" (mocking what you don't own)
- pytest documentation: "Good Integration Practices", fixtures, markers, strict mode
- mutmut documentation: Configuration and workflow
- Playwright documentation (Context7)
