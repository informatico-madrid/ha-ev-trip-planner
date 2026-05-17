# Requirements: Test Architecture Reorganization

## Goal

Reorganize 104 flat Python test files into `unit/`, `integration/`, `e2e/` layer structure with `test_{module}_{aspect}.py` naming. Consolidate redundant file groups. Install missing testing tools. Configure pytest strict mode, importlib mode, and markers. Zero test regressions throughout -- `fail_under=100` gates every phase.

## User Stories

### US-1: Layer Separation
**As a** developer
**I want** tests organized into `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `tests/helpers/`
**So that** I can run only unit or only integration tests, and new tests have an obvious home

**Acceptance Criteria:**
- [ ] AC-1.1: `tests/unit/` directory exists with unit-scoped test files
- [ ] AC-1.2: `tests/integration/` directory exists with integration-scoped test files
- [ ] AC-1.3: `tests/e2e/` retains existing TypeScript Playwright tests (unchanged)
- [ ] AC-1.4: `tests/fixtures/` retains existing fixture data (unchanged)
- [ ] AC-1.5: `tests/helpers/` directory created for shared test utilities extracted from `__init__.py`
- [ ] AC-1.6: `make test` passes with same 1,821 test count after reorganization
- [ ] AC-1.7: `make test-cover` passes with `fail_under=100` after reorganization

### US-2: Trip Manager Test Consolidation
**As a** developer
**I want** trip-related test files consolidated from 18 files into at most 3 focused files
**So that** related test behaviors are discoverable and maintainable

**Acceptance Criteria:**
- [ ] AC-2.1: 13 `test_trip_manager*.py` files consolidated into at most 3 files (plus 5 `test_trip_*.py` files evaluated)
- [ ] AC-2.2: Merged files follow `test_trip_manager_{aspect}.py` naming
- [ ] AC-2.3: All trip-related tests retain original assertions (no weakened coverage)
- [ ] AC-2.4: AAA pattern (Arrange-Act-Assert) visible in consolidated tests
- [ ] AC-2.5: Consolidated files pass with zero test regressions

### US-3: Config Flow Test Consolidation
**As a** developer
**I want** 6 config_flow test files consolidated into at most 2 files
**So that** config flow tests are not scattered across milestone and coverage artifacts

**Acceptance Criteria:**
- [ ] AC-3.1: 6 `test_config_flow*.py` files consolidated into at most 2 files
- [ ] AC-3.2: Renamed to `test_config_flow_{aspect}.py` convention
- [ ] AC-3.3: All config flow assertions retained, no weakened coverage

### US-4: Coverage-Driven Test Cleanup
**As a** developer
**I want** coverage-driven test files renamed or merged into behavior-driven tests
**So that** file names describe WHAT is tested, not HOW coverage was achieved

**Acceptance Criteria:**
- [ ] AC-4.1: Files named `*_coverage*`, `*_cover*`, `*_missing*` evaluated for consolidation or rename
- [ ] AC-4.2: Consolidated files use behavior-based names (`test_{module}_{behavior}`)
- [ ] AC-4.3: Coverage remains at 100% after cleanup

### US-5: Assert-True Violations Fixed
**As a** developer
**I want** all `assert True` violations replaced with real assertions or removed
**So that** every test actually validates behavior

**Acceptance Criteria:**
- [ ] AC-5.1: `assert True` in `test_missing_coverage.py` replaced with meaningful assertion or test removed
- [ ] AC-5.2: `assert True` in `test_init.py` replaced with meaningful assertion or test removed
- [ ] AC-5.3: `grep -r "assert True" tests/` returns zero matches in Python files
- [ ] AC-5.4: Coverage remains 100% (if test was covering real code, replacement assertion covers same path)

### US-6: Bug-Regression Test Consolidation
**As a** developer
**I want** orphaned bug-finding tests consolidated into behavior-driven regression tests
**So that** regression coverage is organized by module, not by historical bug number

**Acceptance Criteria:**
- [ ] AC-6.1: 10 bug-named test files (`*_bug*.py`) evaluated for consolidation
- [ ] AC-6.2: Consolidated tests use descriptive names: `test_{module}_{scenario}_{expected}`
- [ ] AC-6.3: Each retained regression test preserves original bug-catching assertion
- [ ] AC-6.4: Bug tests merged into module-appropriate files where readability improves

### US-7: Fixture Refactoring
**As a** developer
**I want** the monolithic `conftest.py` split into scoped fixtures and duplicate `mock_hass` eliminated
**So that** test setup is modular and DRY

**Acceptance Criteria:**
- [ ] AC-7.1: `conftest.py` (702 LOC, 23 fixtures) split into root + layer-specific conftest files
- [ ] AC-7.2: Root conftest.py contains only truly shared fixtures
- [ ] AC-7.3: `tests/unit/conftest.py` and/or `tests/integration/conftest.py` contain layer-specific fixtures
- [ ] AC-7.4: Duplicate inline `mock_hass` definitions (28 files) consolidated into conftest fixtures
- [ ] AC-7.5: All tests pass after fixture refactoring

### US-8: Testing Tools Installation
**As a** developer
**I want** time-machine, flake8-pytest-style, and hypothesis installed
**So that** modern testing patterns are available for current and future specs

**Acceptance Criteria:**
- [ ] AC-8.1: `time-machine` listed in dev dependencies and importable
- [ ] AC-8.2: `flake8-pytest-style` listed in dev dependencies and configured in pre-commit/flake8
- [ ] AC-8.3: `hypothesis` listed in dev dependencies and importable
- [ ] AC-8.4: All existing tests pass with new dependencies installed

### US-9: Pytest Strict Configuration
**As a** developer
**I want** pytest strict mode, importlib import mode, and registered markers configured
**So that** silent failures from typos or unregistered markers are caught early

**Acceptance Criteria:**
- [ ] AC-9.1: `strict = true` set in `[tool.pytest.ini_options]` (pytest 9.0+)
- [ ] AC-9.2: `import_mode = "importlib"` set in `[tool.pytest.ini_options]`
- [ ] AC-9.3: Markers `unit`, `integration`, `slow` registered in `pyproject.toml`
- [ ] AC-9.4: `--strict-markers` and `--strict-config` in `addopts`
- [ ] AC-9.5: `pytest --co` succeeds without warnings about unregistered markers
- [ ] AC-9.6: All tests pass with strict configuration enabled

### US-10: Baseline and Checkpoint Verification
**As a** developer
**I want** baseline metrics captured before reorganization and verified at each checkpoint
**So that** any regression is detected immediately, not at spec completion

**Acceptance Criteria:**
- [ ] AC-10.1: Baseline captured: `make test-cover` output (1,821 tests, 100% coverage)
- [ ] AC-10.2: Baseline captured: `make e2e` and `make e2e-soc` pass
- [ ] AC-10.3: Checkpoint verification after each phase: test count = 1,821 (or higher if bug fixes add tests)
- [ ] AC-10.4: Checkpoint verification after each phase: coverage = 100%
- [ ] AC-10.5: `make e2e` and `make e2e-soc` verified at final checkpoint (E2E unaffected by Python changes)

### US-11: Config Path Updates
**As a** developer
**I want** all config files updated to reflect the new test structure
**So that** Makefile, pyproject.toml, and mutmut all target the correct paths

**Acceptance Criteria:**
- [ ] AC-11.1: `testpaths` in pyproject.toml updated to `["tests/unit", "tests/integration"]`
- [ ] AC-11.2: `tests_dir` in `[tool.mutmut]` updated to `["tests/unit/", "tests/integration/"]`
- [ ] AC-11.3: Makefile test targets updated from `pytest tests --ignore=tests/e2e/` to target new paths
- [ ] AC-11.4: Coverage source paths in pyproject.toml remain correct (source unchanged, tests omitted)
- [ ] AC-11.5: `.pre-commit-config.yaml` verified to work with new directory structure

### US-12: Mutmut Excluded Files Evaluation
**As a** developer
**I want** files in `tests_excluded_from_mutmut/` evaluated for placement in the new structure
**So that** the old exclusion directory has a clear disposition

**Acceptance Criteria:**
- [ ] AC-12.1: `test_timezone_utc_vs_local_bug.py` evaluated: kept, moved, or deleted with documented rationale
- [ ] AC-12.2: `test_vehicle_controller_event.py` evaluated: kept, moved, or deleted with documented rationale
- [ ] AC-12.3: If files are kept, they are placed in appropriate layer (unit/ or integration/)
- [ ] AC-12.4: If files are moved, mutmut exclusion list updated accordingly

### US-13: Bug Discovery During Reorganization
**As a** developer
**I want** bugs discovered during test reorganization fixed immediately
**So that** the test suite quality improves as a side effect of reorganization

**Acceptance Criteria:**
- [ ] AC-13.1: Bugs found during file moves, consolidation, or fixture refactoring are fixed
- [ ] AC-13.2: Each bug fix documented as a finding in commit message or .progress.md
- [ ] AC-13.3: Bug fixes do not weaken existing test coverage (still 100%)
- [ ] AC-13.4: If a bug fix adds new test cases, test count may increase (allowed, not required)

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Create `tests/unit/` directory and move unit-scoped test files there | High | Directory exists; `make test` passes with same test count |
| FR-2 | Create `tests/integration/` directory and move integration-scoped test files there | High | Directory exists; integration tests import from `homeassistant.*` |
| FR-3 | Create `tests/helpers/` directory with shared utilities from `tests/__init__.py` | High | FakeTripStorage, FakeEMHASSPublisher, factories extracted; 90+ importing files updated |
| FR-4 | Consolidate 13 `test_trip_manager*.py` files into at most 3 focused files | High | Original 13 files gone; merged files pass all assertions |
| FR-5 | Consolidate 5 remaining `test_trip_*.py` files into appropriate trip test files | Medium | Evaluated for merge; kept separate only if readability requires it |
| FR-6 | Consolidate 6 `test_config_flow*.py` into at most 2 files | High | Original 6 files gone; merged files pass all assertions |
| FR-7 | Evaluate and consolidate/rename 26 coverage-driven test files | Medium | No files with `_coverage`/`_cover`/`_missing` suffixes remain |
| FR-8 | Fix 2 `assert True` violations with real assertions | High | `grep -r "assert True" tests/` returns 0 Python matches |
| FR-9 | Consolidate 10 bug-named test files into behavior-driven tests | Medium | Bug-catching assertions preserved; names describe behavior |
| FR-10 | Split conftest.py (702 LOC, 23 fixtures) into root + layer conftests | High | Root conftest < 200 LOC; layer conftests contain scoped fixtures |
| FR-11 | Eliminate 28 duplicate inline `mock_hass` definitions | High | No test file defines its own `mock_hass`; all use conftest fixture |
| FR-12 | Install `time-machine` as dev dependency | High | `pip install time-machine` succeeds; listed in pyproject.toml |
| FR-13 | Install `flake8-pytest-style` as dev dependency | High | Listed in pyproject.toml; flake8 integration verified |
| FR-14 | Install `hypothesis` as dev dependency | High | `pip install hypothesis` succeeds; listed in pyproject.toml |
| FR-15 | Configure `strict = true` in pytest config | High | `pyproject.toml` has `strict = true` under `[tool.pytest.ini_options]` |
| FR-16 | Configure `import_mode = "importlib"` in pytest config | High | `pyproject.toml` has `import_mode = "importlib"` |
| FR-17 | Register markers `unit`, `integration`, `slow` in pytest config | High | `pyproject.toml` has all three markers under `[tool.pytest.ini_options].markers` |
| FR-18 | Update `testpaths` to `["tests/unit", "tests/integration"]` | High | `make test` discovers all 1,821+ tests |
| FR-19 | Update mutmut `tests_dir` to `["tests/unit/", "tests/integration/"]` | High | `mutmut run --list` discovers all Python test files |
| FR-20 | Update Makefile test targets for new paths | High | `make test`, `make test-cover`, `make test-verbose` all pass |
| FR-21 | Capture baseline metrics before any changes | High | Baseline output saved: test count, coverage, e2e pass/fail |
| FR-22 | Verify at each checkpoint: test count >= 1,821 | High | Checkpoint after each phase; regression = revert |
| FR-23 | Verify at each checkpoint: coverage = 100% | High | `fail_under = 100` must pass at every checkpoint |
| FR-24 | Verify `make e2e` and `make e2e-soc` pass at final checkpoint | High | E2E tests unaffected by Python test reorganization |
| FR-25 | Evaluate `tests_excluded_from_mutmut/` files for new structure placement | Medium | Each file has documented disposition (kept/moved/deleted) |
| FR-26 | Update coverage source paths in pyproject.toml if needed | Medium | `coverage run` still targets correct source; tests still omitted |
| FR-27 | Fix bugs discovered during reorganization | Medium | Bug documented; fix does not drop coverage below 100% |
| FR-28 | Apply `test_{module}_{aspect}.py` naming convention to all moved files | Medium | File names describe what module and what aspect is tested |
| FR-29 | Ensure `tests/__init__.py` extraction is a separate commit from file moves | High | Two distinct commits; each passes 100% coverage independently |
| FR-30 | Keep `panel.test.js` in `tests/` root (Jest, not Playwright) | High | File not moved to `e2e/` |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test count stability | Test count delta | 0 (1,821 collected, allowing increase from bug fixes) |
| NFR-2 | Coverage stability | `fail_under` gate | 100% at every checkpoint |
| NFR-3 | E2E isolation | E2E test changes | 0 TypeScript files modified |
| NFR-4 | Source code isolation | Source file changes | 0 source files modified (test code only) |
| NFR-5 | Revert safety | Phased commits | Each phase is independent commit; revertible |
| NFR-6 | Mutation compatibility | mutmut discovery | All Python test files discovered after reorganization |
| NFR-7 | Execution time | Test suite duration | No more than 10% increase from baseline |
| NFR-8 | Import correctness | Import errors | 0 ImportError / ModuleNotFoundError |

## Glossary

- **ARN-008**: Architecture rule requiring test layer separation (unit/integration/e2e)
- **fail_under=100**: Coverage quality gate -- any uncovered line fails the build
- **conftest.py**: pytest fixture discovery file; fixtures available to tests in same directory and subdirectories
- **mock_hass**: Mocked HomeAssistant instance used by 28 test files with duplicate definitions
- **FakeTripStorage / FakeEMHASSPublisher**: Hand-crafted test doubles (Meszaros "Fake" pattern) -- correct, keep
- **MockConfigEntry**: HA framework mock for config entry lifecycle -- indicates integration test weight
- **`tests_excluded_from_mutmut/`**: Directory with 2 test files excluded from mutation testing
- **panel.test.js**: Jest-based panel test in `tests/` root; NOT a Playwright E2E test
- **`--import-mode=importlib`**: Modern pytest import mode that avoids sys.path issues with subdirectories
- **strict = true**: pytest 9.0+ config enabling strict_markers, strict_config, etc.
- **AAA pattern**: Arrange-Act-Assert test structure for readability
- **Phase**: One commit in the phased reorganization strategy; each phase must pass 100% independently

## Out of Scope

- Source code changes (only test code and config files)
- Coverage improvement beyond maintaining 100% (that's Spec 6)
- Mutation score improvement (that's Spec 5)
- `pragma: no cover` removal (that's Spec 6)
- E2E TypeScript test changes (already in correct directory)
- Adding new test markers to existing tests (marker application deferred; registration in scope)
- Per-module subdirectories under unit/ (optional future improvement)
- Adding `spec=` to all MagicMock instances (quality improvement, not structural)
- Replacing MagicMock with AsyncMock for async methods (quality improvement)
- Eliminating 540 `patch()` string-path calls (too risky for this spec)
- Improving parametrization beyond current 13 tests (quality improvement)
- Hardcoded magic number extraction (low priority)

## Dependencies

- **Spec 1 (dead-code)**: Completed. Baseline of 1,821 tests established.
- **Spec 3 (SOLID Refactor)**: Blocked by this spec. Needs test structure before source module splits.
- **Spec 5 (Mutation Ramp)**: Blocked by this spec. Uses new `tests_dir` paths.
- **Spec 7 (Lint/Format/Type)**: Will enforce flake8-pytest-style after this spec installs it.
- **pytest 9.0+**: Required for `strict = true`. Verify version in venv.
- **Existing `fail_under = 100`**: Makes this spec HIGH risk. Every phase must pass.

## Constraints

- **C-1**: No source code modifications. Only test code, config files, and Makefile.
- **C-2**: Zero test regressions. `fail_under = 100` gates every commit.
- **C-3**: E2E tests untouched. TypeScript files in `tests/e2e/` and `tests/e2e-dynamic-soc/` not modified.
- **C-4**: `panel.test.js` stays in `tests/` root (Jest, not Playwright).
- **C-5**: `tests/__init__.py` extraction must be separate commit from file moves.
- **C-6**: Phased commits. Each commit independently revertible and passing 100%.
- **C-7**: No new test coverage targets. Maintain 100%, don't chase new lines.
- **C-8**: E2E verification uses `make e2e` and `make e2e-soc` commands (not direct playwright).
- **C-9**: Bug fixes during reorganization are in-scope. Active bug hunting is not.

## Success Criteria

- `make test` passes with >= 1,821 tests collected
- `make test-cover` passes with 100% coverage
- `make e2e` and `make e2e-soc` pass (unchanged)
- Tests organized into `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `tests/helpers/`
- 13 `test_trip_manager*.py` consolidated to <= 3 files
- 6 `test_config_flow*.py` consolidated to <= 2 files
- 0 `assert True` violations
- conftest.py split from 702 LOC to scoped fixtures
- time-machine, flake8-pytest-style, hypothesis installed
- pytest strict mode, importlib mode, markers configured
- All config paths (pyproject.toml, Makefile, mutmut) updated

## Verification Contract

**Project type**: library

**Entry points**:
- `make test` (pytest via Makefile)
- `make test-cover` (pytest + coverage via Makefile)
- `make test-verbose` (pytest verbose via Makefile)
- `make e2e` (Playwright TypeScript tests, port 8123)
- `make e2e-soc` (Playwright TypeScript tests, port 8123)
- `pytest --co -q` (test discovery)
- `mutmut run --list` (mutation test discovery)
- `pyproject.toml` (pytest, coverage, mutmut config)
- `Makefile` (test targets)
- `tests/conftest.py` + `tests/unit/conftest.py` + `tests/integration/conftest.py`
- `tests/__init__.py` -> `tests/helpers/` extraction

**Observable signals**:
- PASS looks like: `make test` exits 0, reports 1,821+ tests collected and passed; `make test-cover` reports 100% coverage; `make e2e` and `make e2e-soc` exit 0; `pytest --co -q` lists all tests; `mutmut run --list` discovers all Python test files; `grep -r "assert True" tests/` finds 0 Python matches; directory listing shows `tests/unit/`, `tests/integration/`, `tests/helpers/`
- FAIL looks like: `make test` exits non-zero (import error, assertion failure, wrong test count); `make test-cover` reports < 100%; `pytest --co -q` shows missing tests; TypeError from broken imports after file moves; `mutmut run --list` misses files; `grep -r "assert True" tests/` returns matches

**Hard invariants**:
- `fail_under = 100` must pass after every commit
- E2E TypeScript tests must not be modified
- `panel.test.js` must stay in `tests/` root
- Source code (`custom_components/`) must not be modified
- Coverage `source` path must remain `custom_components/ev_trip_planner`
- `asyncio_mode = "auto"` must remain configured
- `tests/fixtures/` data files must not be moved or modified

**Seed data**:
- Full test suite with 1,821 tests across 104 files
- conftest.py with 702 LOC and 23 fixtures
- `tests/__init__.py` with 198 LOC (fakes, factories, constants)
- 2 files in `tests_excluded_from_mutmut/`
- E2E Playwright suites in `tests/e2e/` (8 files) and `tests/e2e-dynamic-soc/` (2+1 files)
- `panel.test.js` in `tests/` root

**Dependency map**:
- `pyproject.toml`: pytest config, coverage config, mutmut config, dependency list
- `Makefile`: 6 test targets that reference `tests/` paths
- `.pre-commit-config.yaml`: may reference test paths for linting
- `tests/__init__.py`: imported by 90+ test files (extraction must be atomic)
- `tests/conftest.py`: fixtures used by all test files (split must be atomic)
- `tests_excluded_from_mutmut/`: referenced by mutmut config
- Spec 3 (SOLID Refactor): blocked until this spec establishes test structure
- Spec 5 (Mutation Ramp): uses `tests_dir` updated by this spec
- Spec 7 (Lint/Format/Type): enforces flake8-pytest-style installed by this spec

**Escalate if**:
- Any phase causes test count to DROP below 1,821 (regression -- revert immediately)
- Coverage drops below 100% at any checkpoint (broken import -- revert and fix)
- File move causes circular imports between `tests/__init__.py` and `tests/helpers/`
- Consolidation of bug tests would lose a bug-catching assertion (keep separate)
- Integration/unit classification is ambiguous for a specific file (human judgment needed)
- `make e2e` or `make e2e-soc` fails after Python test changes (investigate -- should be unrelated)
- mutmut cannot discover tests after path update (config error -- fix before proceeding)

## Unresolved Questions

1. **Exact file-to-layer classification**: 47 files lack clear single-module mapping. Classification script needed to automate; manual review for edge cases.
2. **Consolidation boundaries for trip tests**: 18 trip-related files into <= 3 -- which groupings maximize readability? Aspect-based (core, calculations, emhass) vs behavior-based?
3. **`tests/__init__.py` extraction scope**: Extract all 198 LOC to helpers/, or only fakes and factories? Constants could stay or move.
4. **Marker application timing**: This spec registers markers. When do tests get `@pytest.mark.unit` / `@pytest.mark.integration` annotations? Defer to implementation?
5. **`tests_excluded_from_mutmut/` disposition**: Move files into new structure, or leave in exclusion directory? Spec 5 may need them excluded still.

## Next Steps

1. Approve requirements (user review)
2. Capture baseline metrics (`make test-cover`, `make e2e`, `make e2e-soc`)
3. Phase 1: Install tools (time-machine, flake8-pytest-style, hypothesis) + configure pytest (strict, importlib, markers)
4. Phase 2: Create directory structure (`unit/`, `integration/`, `helpers/`) + extract `__init__.py`
5. Phase 3: Classify and move files to layers
6. Phase 4: Consolidate file groups (trip_manager, config_flow, coverage, bug)
7. Phase 5: Fix `assert True` violations
8. Phase 6: Split conftest.py, eliminate duplicate mock_hass
9. Phase 7: Update config paths (pyproject.toml, Makefile, mutmut)
10. Phase 8: Final checkpoint verification
