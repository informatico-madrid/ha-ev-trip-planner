# Tasks: Test Architecture Reorganization

## Phase 1: Make It Work (POC) — Tools + Config + Structure + Extraction + Classification + Move

Focus: Install tools, configure pytest, create directory structure, extract helpers, classify files, move all files to unit/ first. Proves the structure works end-to-end.

- [x] 1.1 Capture baseline metrics
  - **Do**: Run `make test` and capture test count. Run `make test-cover` and capture coverage. Save output to `specs/2-test-reorg/.baseline.txt`.
  - **Files**: specs/2-test-reorg/.baseline.txt
  - **Done when**: Baseline file exists with 1,821+ tests and 100% coverage recorded
  - **Verify**: `grep -q "1821 passed" specs/2-test-reorg/.baseline.txt && grep -q "100%" specs/2-test-reorg/.baseline.txt && echo BASELINE_PASS`
  - **Commit**: `chore(test-reorg): capture baseline metrics`
  - _Requirements: FR-21, AC-10.1_

- [x] 1.2 [P] Install time-machine as dev dependency
  - **Do**: Add `time-machine` to dev dependencies in pyproject.toml. Run `pip install time-machine` in venv.
  - **Files**: pyproject.toml
  - **Done when**: `time-machine` importable; listed in pyproject.toml
  - **Verify**: `.venv/bin/python -c "import time_machine; print(time_machine.__version__)" && echo PASS`
  - **Commit**: `build(test-reorg): add time-machine dev dependency`
  - _Requirements: FR-12, AC-8.1_

- [x] 1.3 [P] Install hypothesis as dev dependency
  - **Do**: Add `hypothesis` to dev dependencies in pyproject.toml. Run `pip install hypothesis` in venv.
  - **Files**: pyproject.toml
  - **Done when**: `hypothesis` importable; listed in pyproject.toml
  - **Verify**: `.venv/bin/python -c "import hypothesis; print(hypothesis.__version__)" && echo PASS`
  - **Commit**: `build(test-reorg): add hypothesis dev dependency`
  - _Requirements: FR-14, AC-8.3_

- [x] 1.4 [P] Install flake8-pytest-style as dev dependency
  - **Do**: Add `flake8-pytest-style` to dev dependencies in pyproject.toml. Run `pip install flake8-pytest-style` in venv.
  - **Files**: pyproject.toml
  - **Done when**: `flake8-pytest-style` importable; listed in pyproject.toml
  - **Verify**: `.venv/bin/python -c "import flake8_pytest_style; print('OK')" && echo PASS`
  - **Commit**: `build(test-reorg): add flake8-pytest-style dev dependency`
  - _Requirements: FR-13, AC-8.2_

- [x] 1.5 [VERIFY] Quality checkpoint: new deps + existing tests pass
  - **Do**: Run `make test` and `make test-cover` to verify all 1,821 tests pass at 100% with new deps
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: 1,821+ tests pass, coverage 100%, no warnings
  - **Commit**: None (no fixes needed unless failure)

- [x] 1.6 Configure pytest strict mode, importlib, and markers
  - **Do**: Update `[tool.pytest.ini_options]` in pyproject.toml: add `import_mode = "importlib"`, `strict = true`, markers (`unit`, `integration`, `slow`), add `--strict-markers` and `--strict-config` to addopts. Keep existing asyncio_mode, filterwarnings, etc.
  - **Files**: pyproject.toml
  - **Done when**: `pytest --co -q` succeeds without marker warnings; config has all 6 new fields
  - **Verify**: `grep -q "import_mode" pyproject.toml && grep -q "strict = true" pyproject.toml && grep -q "unit:" pyproject.toml && make test 2>&1 | tail -3 | grep -q "passed" && echo VERIFY_PASS`
  - **Commit**: `feat(test-reorg): configure pytest strict mode, importlib, and markers`
  - _Requirements: FR-15, FR-16, FR-17, AC-9.1-9.6_

- [x] 1.7 [VERIFY] Quality checkpoint: strict mode + importlib works
  - **Do**: Run `make test` and `make test-cover` to verify strict mode and importlib cause no regressions
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: 1,821+ tests pass at 100%, no warnings about unregistered markers
  - **Commit**: None

- [x] 1.8 Create tests/helpers/ directory with constants.py
  - **Do**: Create `tests/helpers/` dir. Extract CONSTANTS section (lines 10-53) from `tests/__init__.py` to `tests/helpers/constants.py`. Create `tests/helpers/__init__.py` with re-export of all public symbols.
  - **Files**: tests/helpers/constants.py, tests/helpers/__init__.py
  - **Done when**: Constants file exists; helpers/__init__.py re-exports TEST_VEHICLE_ID, TEST_CONFIG, etc.
  - **Verify**: `.venv/bin/python -c "from tests.helpers.constants import TEST_VEHICLE_ID; assert TEST_VEHICLE_ID == 'coche1'" && echo PASS`
  - **Commit**: `refactor(test-reorg): extract constants to tests/helpers/constants.py`
  - _Requirements: FR-3, AC-1.5_

- [x] 1.9 [P] Create tests/helpers/fakes.py
  - **Do**: Extract FakeTripStorage and FakeEMHASSPublisher classes from `tests/__init__.py` to `tests/helpers/fakes.py`. Update `tests/helpers/__init__.py` re-exports.
  - **Files**: tests/helpers/fakes.py, tests/helpers/__init__.py
  - **Done when**: FakeTripStorage and FakeEMHASSPublisher importable from tests.helpers
  - **Verify**: `.venv/bin/python -c "from tests.helpers.fakes import FakeTripStorage, FakeEMHASSPublisher; print('OK')" && echo PASS`
  - **Commit**: `refactor(test-reorg): extract fakes to tests/helpers/fakes.py`
  - _Requirements: FR-3, AC-1.5_

- [x] 1.10 [P] Create tests/helpers/factories.py
  - **Do**: Extract `create_mock_trip_manager`, `create_mock_coordinator`, `create_mock_ev_config_entry`, `setup_mock_ev_config_entry` from `tests/__init__.py` to `tests/helpers/factories.py`. Update `tests/helpers/__init__.py` re-exports.
  - **Files**: tests/helpers/factories.py, tests/helpers/__init__.py
  - **Done when**: All 4 factory functions importable from tests.helpers
  - **Verify**: `.venv/bin/python -c "from tests.helpers.factories import create_mock_trip_manager; print('OK')" && echo PASS`
  - **Commit**: `refactor(test-reorg): extract factories to tests/helpers/factories.py`
  - _Requirements: FR-3, AC-1.5_

- [x] 1.11 Replace tests/__init__.py with re-export shim
  - **Do**: Replace `tests/__init__.py` (198 LOC) with a thin re-export shim that imports all symbols from `tests.helpers`. This ensures backward compat for any `from tests import X` usage.
  - **Files**: tests/__init__.py
  - **Done when**: `from tests import FakeTripStorage` still works; file is < 20 LOC
  - **Verify**: `.venv/bin/python -c "from tests import FakeTripStorage, TEST_VEHICLE_ID, create_mock_trip_manager; print('OK')" && echo PASS`
  - **Commit**: `refactor(test-reorg): replace tests/__init__.py with re-export shim`
  - _Requirements: FR-29, C-5_

- [x] 1.12 Update 4 import statements in test files
  - **Do**: Update imports in `test_coverage_100_percent.py`, `test_trip_manager_missing_coverage.py`, `test_trip_manager_cover_more.py`, `test_trip_manager_core.py` from `from tests import X` to `from tests.helpers import X` (or keep as-is since shim handles it — verify both work and pick cleaner option).
  - **Files**: tests/test_coverage_100_percent.py, tests/test_trip_manager_missing_coverage.py, tests/test_trip_manager_cover_more.py, tests/test_trip_manager_core.py
  - **Done when**: All 4 files import from tests.helpers; `make test` passes
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Commit**: `refactor(test-reorg): update imports from tests to tests.helpers`
  - _Requirements: FR-3, C-5_

- [x] 1.13 [VERIFY] Quality checkpoint: helpers extraction complete
  - **Do**: Run `make test` and `make test-cover` to verify extraction did not break anything
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: 1,821+ tests pass at 100%
  - **Commit**: None

- [x] 1.14 Create directory structure: tests/unit/ and tests/integration/
  - **Do**: Create `tests/unit/` and `tests/integration/` directories. Create empty `__init__.py` in each. Create stub `conftest.py` in each (empty initially, just `# Layer-specific fixtures`).
  - **Files**: tests/unit/__init__.py, tests/unit/conftest.py, tests/integration/__init__.py, tests/integration/conftest.py
  - **Done when**: Directories exist with __init__.py and stub conftest.py
  - **Verify**: `test -d tests/unit && test -d tests/integration && test -f tests/unit/conftest.py && test -f tests/integration/conftest.py && echo PASS`
  - **Commit**: `feat(test-reorg): create unit/ and integration/ directories with stub conftest`
  - _Requirements: FR-1, FR-2, AC-1.1, AC-1.2_

- [x] 1.15 [VERIFY] Quality checkpoint: directory structure created
  - **Do**: Run `make test` to verify new directories don't break discovery
  - **Verify**: `make test 2>&1 | tail -3 | grep -q "passed" && echo VERIFY_PASS`
  - **Done when**: 1,821+ tests pass
  - **Commit**: None

- [x] 1.16 POC: Move 2 representative files to prove structure works
  - **Do**: Move `tests/test_calculations.py` to `tests/unit/test_calculations.py` (unit representative). Move `tests/test_init.py` to `tests/integration/test_init.py` (integration representative). Use `git mv`. Verify import_mode=importlib handles subdirectory imports correctly.
  - **Files**: tests/unit/test_calculations.py, tests/integration/test_init.py
  - **Done when**: Both files moved; `make test-cover` passes at 100%
  - **Verify**: `test -f tests/unit/test_calculations.py && test -f tests/integration/test_init.py && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo POC_FILE_MOVE_PASS`
  - **Commit**: `refactor(test-reorg): POC move 2 files to prove structure works`
  - _Requirements: FR-1, FR-2, AC-1.6, AC-1.7_

- [x] 1.17 [VERIFY] POC checkpoint: structure proven with representative files
  - **Do**: Run `make test` and `make test-cover`. Verify test count unchanged. This proves import_mode=importlib works and fail_under=100 passes with subdirectory structure.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo POC_PROVEN`
  - **Done when**: 1,821+ tests pass at 100% — structure proven, safe to proceed with bulk move
  - **Commit**: None

- [x] 1.18 Move 74 unit test files to tests/unit/ (excluding POC-moved test_calculations.py)
  - **Do**: Move all 73 remaining files that do NOT have `from homeassistant` imports to `tests/unit/`. Use `git mv` for each file. Excludes test_calculations.py (already in POC task 1.16).
  - **Files**: 73 test files moved to tests/unit/
  - **Done when**: All 73 files in tests/unit/; `pytest tests/unit/ --co -q` finds them all
  - **Verify**: `pytest tests/unit/ --co -q 2>/dev/null | tail -1 | grep -q "test" && echo UNIT_PASS`
  - **Commit**: `refactor(test-reorg): move 73 unit test files to tests/unit/`
  - _Requirements: FR-1, AC-1.1, AC-1.6_

- [x] 1.19 [VERIFY] Quality checkpoint: unit files moved
  - **Do**: Run `pytest tests/unit/ --co -q` and verify test count. Run `make test-cover` to verify 100%.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All 1,821+ tests discovered and pass at 100%
  - **Commit**: None

- [x] 1.20 Move 30 integration test files to tests/integration/ (excluding POC-moved test_init.py)
  - **Do**: Move all 29 remaining files with `from homeassistant` imports to `tests/integration/`. Use `git mv` for each file. Excludes test_init.py (already in POC task 1.16). Files: test_config_entry_not_ready.py, test_config_flow.py, test_config_flow_core.py, test_config_flow_milestone3.py, test_config_flow_missing.py, test_config_updates.py, test_coordinator.py, test_coverage_edge_cases.py, test_emhass_adapter.py, test_emhass_soft_delete.py, test_functional_emhass_sensor_updates.py, test_integration_uninstall.py, test_migrate_entry.py, test_notifications.py, test_parse_trip_datetime_error_paths.py, test_post_restart_persistence.py, test_power_profile_tdd.py, test_presence_monitor.py, test_presence_monitor_soc.py, test_renault_integration_issues.py, test_restore_sensor.py, test_sensor_coverage.py, test_services_core.py, test_trip_calculations.py, test_trip_emhass_sensor.py, test_trip_manager_core.py, test_trip_manager_power_profile.py, test_user_real_data_simple.py, test_vehicle_controller.py
  - **Files**: 29 test files moved to tests/integration/
  - **Done when**: All 29 files in tests/integration/; `pytest tests/integration/ --co -q` finds them
  - **Verify**: `pytest tests/integration/ --co -q 2>/dev/null | tail -1 | grep -q "test" && echo INT_PASS`
  - **Commit**: `refactor(test-reorg): move 29 integration test files to tests/integration/`
  - _Requirements: FR-2, AC-1.2, AC-1.6_

- [ ] 1.21 [VERIFY] POC Checkpoint: full structure works
  - **Do**: Run `make test` and `make test-cover`. Verify test count = 1,821+. Verify coverage = 100%. Run `pytest --co -q` to count tests in unit/ and integration/. Verify tests/fixtures/ unchanged: `git diff --name-only tests/fixtures/` returns empty.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && git diff --name-only tests/fixtures/ | wc -l | grep -q "^0$" && echo POC_PASS`
  - **Done when**: 1,821+ tests pass at 100% coverage in new structure; fixtures data untouched
  - **Commit**: None

## Phase 2: Refactoring — Consolidation + Rename + Conftest Split

Focus: Consolidate trip_manager files, config_flow files. Rename bug/coverage files. Fix assert True. Split conftest. Clean up.

- [ ] 2.1 Consolidate trip_manager files: create test_trip_manager_core.py
  - **Do**: Merge content from `test_trip_manager.py` (unit), `test_trip_manager_fix_branches.py` (unit), and the unit-scoped tests from the moved files into a single consolidated file. Target: tests/unit/test_trip_manager_core.py. Use AAA pattern. Ensure all original assertions preserved.
  - **Files**: tests/unit/test_trip_manager_core.py (existing, augmented with tests from test_trip_manager.py and test_trip_manager_fix_branches.py)
  - **Done when**: Consolidated file passes all merged tests; original source files can be deleted
  - **Verify**: `pytest tests/unit/test_trip_manager_core.py -v --tb=short 2>&1 | tail -5 | grep -q "passed" && echo PASS`
  - **Commit**: `refactor(test-reorg): consolidate trip_manager core tests`
  - _Requirements: FR-4, AC-2.1, AC-2.2, AC-2.3, AC-2.4_

- [ ] 2.2 Consolidate trip_manager files: create test_trip_manager_calculations.py
  - **Do**: Merge content from `test_trip_manager_calculations.py`, `test_trip_manager_more_coverage.py`, `test_trip_manager_missing_coverage.py`, `test_trip_manager_cover_more.py`, `test_trip_manager_cover_line1781.py` into a single consolidated file in tests/unit/. Preserve all assertions. Rename coverage-driven test functions to behavior-based names.
  - **Files**: tests/unit/test_trip_manager_calculations.py (consolidated)
  - **Done when**: Consolidated file passes; 5 source files deleted
  - **Verify**: `pytest tests/unit/test_trip_manager_calculations.py -v --tb=short 2>&1 | tail -5 | grep -q "passed" && echo PASS`
  - **Commit**: `refactor(test-reorg): consolidate trip_manager calculation tests`
  - _Requirements: FR-4, AC-2.1, AC-2.2_

- [ ] 2.3 Consolidate trip_manager files: create test_trip_manager_emhass_sensors.py
  - **Do**: Merge content from `test_trip_manager_emhass.py`, `test_trip_manager_sensor_hooks.py`, `test_trip_manager_entry_lookup.py`, `test_trip_manager_power_profile.py` (integration), `test_trip_manager_datetime_tz.py` into tests/integration/test_trip_manager_emhass_sensors.py. Preserve all assertions. Named by aspect (EMHASS + sensors), not by layer.
  - **Files**: tests/integration/test_trip_manager_emhass_sensors.py (consolidated)
  - **Done when**: Consolidated file passes; 5 source files deleted
  - **Verify**: `pytest tests/integration/test_trip_manager_emhass_sensors.py -v --tb=short 2>&1 | tail -5 | grep -q "passed" && echo PASS`
  - **Commit**: `refactor(test-reorg): consolidate trip_manager EMHASS + sensor tests`
  - _Requirements: FR-4, AC-2.1, AC-2.2, AC-2.5_

- [ ] 2.4 Delete merged trip_manager source files
  - **Do**: Delete the 13 original trip_manager files that were merged into the 3 consolidated files (test_trip_manager.py, test_trip_manager_fix_branches.py, test_trip_manager_calculations.py, test_trip_manager_more_coverage.py, test_trip_manager_missing_coverage.py, test_trip_manager_cover_more.py, test_trip_manager_cover_line1781.py, test_trip_manager_emhass.py, test_trip_manager_sensor_hooks.py, test_trip_manager_entry_lookup.py, test_trip_manager_datetime_tz.py). Keep test_trip_manager_core.py and test_trip_manager_power_profile.py as they are now the consolidated targets.
  - **Files**: 11+ files deleted from tests/unit/ and tests/integration/
  - **Done when**: Only 3 trip_manager test files remain; `make test` passes
  - **Verify**: `ls tests/unit/test_trip_manager*.py tests/integration/test_trip_manager*.py | wc -l | grep -q "^[3-5]$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): delete merged trip_manager source files`
  - _Requirements: FR-4, AC-2.5_

- [ ] 2.5 [VERIFY] Quality checkpoint: trip_manager consolidation
  - **Do**: Run `make test` and `make test-cover` to verify trip consolidation
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All tests pass at 100%
  - **Commit**: None

- [ ] 2.6 Consolidate config_flow files: merge core + issues into test_config_flow.py
  - **Do**: Merge `test_config_flow_core.py` and `test_config_flow_issues.py` into `test_config_flow.py` in tests/integration/. Preserve all assertions. Use AAA pattern.
  - **Files**: tests/integration/test_config_flow.py (augmented)
  - **Done when**: Consolidated file passes; 2 source files can be deleted
  - **Verify**: `pytest tests/integration/test_config_flow.py -v --tb=short 2>&1 | tail -5 | grep -q "passed" && echo PASS`
  - **Commit**: `refactor(test-reorg): consolidate config_flow core + issues`
  - _Requirements: FR-6, AC-3.1, AC-3.2_

- [ ] 2.7 Consolidate config_flow files: merge milestone3 + ux + missing into test_config_flow_options.py
  - **Do**: Merge `test_config_flow_milestone3.py`, `test_config_flow_milestone3_1_ux.py`, `test_config_flow_missing.py` into `test_config_flow_options.py` in tests/integration/. Rename coverage-driven test functions to behavior-based names.
  - **Files**: tests/integration/test_config_flow_options.py (new consolidated file)
  - **Done when**: Consolidated file passes; 3 source files deleted
  - **Verify**: `pytest tests/integration/test_config_flow_options.py -v --tb=short 2>&1 | tail -5 | grep -q "passed" && echo PASS`
  - **Commit**: `refactor(test-reorg): consolidate config_flow options + milestone + missing`
  - _Requirements: FR-6, AC-3.1, AC-3.3_

- [ ] 2.8 [VERIFY] Quality checkpoint: config_flow consolidation
  - **Do**: Run `make test` and `make test-cover`
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All tests pass at 100%
  - **Commit**: None

- [ ] 2.9 Rename 14 bug regression files (remove _bug suffix)
  - **Do**: Rename bug-named files to behavior-based names using `git mv`: test_aggregated_sensor_bug.py -> test_sensor_aggregation.py, test_charging_window_bug_fix.py -> test_charging_window_edge_cases.py, test_def_end_bug_red.py -> test_deferrable_end_boundary.py, test_def_start_window_bug.py -> test_deferrable_start_boundary.py, test_def_total_hours_mismatch_bug.py -> test_deferrable_hours_calculation.py, test_def_total_hours_window_mismatch.py -> test_deferrable_hours_window.py, test_emhass_adapter_def_end_bug.py -> test_emhass_deferrable_end.py, test_emhass_arrays_ordering_bug.py -> test_emhass_array_ordering.py, test_emhass_index_persistence_bug.py -> test_emhass_index_persistence.py, test_emhass_publish_bug.py -> test_emhass_publish_edge_cases.py, test_recurring_day_offset_bug.py -> test_recurring_day_offset.py, test_soc_100_p_deferrable_nom_bug.py -> test_soc_100_deferrable_nominal.py, test_soc_100_propagation_bug.py -> test_soc_100_propagation.py, test_timezone_utc_vs_local_bug.py -> test_timezone_utc_vs_local.py. All 14 are in tests/unit/.
  - **Files**: 14 files renamed in tests/unit/
  - **Done when**: No files with `_bug` suffix remain; `make test` passes
  - **Verify**: `ls tests/unit/test_*bug*.py 2>/dev/null | wc -l | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): rename 14 bug regression files to behavior names`
  - _Requirements: FR-9, AC-6.1, AC-6.2_

- [ ] 2.10 [VERIFY] Quality checkpoint: bug file renames + assertion preservation
  - **Do**: Run `make test` and `make test-cover`. Also verify that no bug-catching assertions were lost during renames by checking assertion counts in renamed files match pre-rename counts (sample 3 files: test_sensor_aggregation.py, test_emhass_index_persistence.py, test_charging_window_edge_cases.py must each contain at least 1 `assert` statement).
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && grep -c "assert" tests/unit/test_sensor_aggregation.py | grep -qv "^0$" && grep -c "assert" tests/unit/test_emhass_index_persistence.py | grep -qv "^0$" && grep -c "assert" tests/unit/test_charging_window_edge_cases.py | grep -qv "^0$" && echo VERIFY_PASS`
  - **Done when**: All tests pass at 100%; renamed files preserve their assertions (AC-6.3)
  - **Commit**: None

- [ ] 2.11 Rename/merge coverage-driven files: dashboard group
  - **Do**: Merge `test_dashboard_cover.py`, `test_dashboard_missing.py`, `test_dashboard_coverage_missing.py` into `test_dashboard.py` in tests/unit/. Rename coverage-driven test functions to behavior-based names. Delete merged source files.
  - **Files**: tests/unit/test_dashboard.py (augmented), 3 files deleted
  - **Done when**: Merged file passes; 3 source files deleted
  - **Verify**: `pytest tests/unit/test_dashboard.py -v --tb=short 2>&1 | tail -5 | grep -q "passed" && echo PASS`
  - **Commit**: `refactor(test-reorg): merge dashboard coverage files into test_dashboard.py`
  - _Requirements: FR-7, AC-4.1, AC-4.2_

- [ ] 2.12 Rename/merge coverage-driven files: sensor + emhass + init groups
  - **Do**: Rename `test_sensor_coverage.py` (integration) to `test_sensor_integration.py`. Rename `test_coverage_edge_cases.py` (integration) to `test_emhass_integration_edge_cases.py`. Merge `test_missing_coverage.py` + `test_coverage_remaining.py` into `test_init_coverage.py` (integration). Rename `test_coverage_100_percent.py` (unit) to `test_init_full_coverage.py`. Rename `test_emhass_adapter_trip_id_coverage.py` (unit) to `test_emhass_adapter_trip_id.py`.
  - **Files**: 6 files renamed/merged
  - **Done when**: No files with `_coverage`/`_cover`/`_missing`/`_remaining` suffixes remain; `make test` passes
  - **Verify**: `ls tests/unit/test_*cover* tests/unit/test_*missing* tests/unit/test_*remaining* tests/integration/test_*cover* tests/integration/test_*missing* tests/integration/test_*remaining* 2>/dev/null | wc -l | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): rename/merge coverage-driven test files`
  - _Requirements: FR-7, AC-4.1, AC-4.2, AC-4.3_

- [ ] 2.13 Rename test_t34_integration_tdd.py (misleading name, actually unit)
  - **Do**: Rename `tests/unit/test_t34_integration_tdd.py` to `tests/unit/test_coordinator_tdd.py` (or appropriate module name based on actual content). Rename `tests/unit/test_t32_and_p11_tdd.py` to behavior-based name.
  - **Files**: tests/unit/test_t34_integration_tdd.py, tests/unit/test_t32_and_p11_tdd.py
  - **Done when**: Files renamed; opaque numeric codes removed from names
  - **Verify**: `test -f tests/unit/test_coordinator_tdd.py && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): rename TDD files with opaque numeric codes`
  - _Requirements: FR-28, AC-4.2_

- [ ] 2.14 [VERIFY] Quality checkpoint: coverage-driven renames complete
  - **Do**: Run `make test` and `make test-cover`
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All tests pass at 100%
  - **Commit**: None

- [ ] 2.15 Fix assert True in test_init_coverage.py (created from test_missing_coverage.py merge)
  - **Do**: Find and replace `assert True` in tests/integration/test_init_coverage.py (created in task 2.12 from merging test_missing_coverage.py + test_coverage_remaining.py). Examine the source code path being covered. Replace with a real assertion that validates the actual behavior, or remove the test if the code path is already covered elsewhere.
  - **Files**: tests/integration/test_init_coverage.py
  - **Done when**: `assert True` replaced with meaningful assertion or test removed; coverage stays 100%
  - **Verify**: `grep -n "assert True" tests/integration/test_init_coverage.py; test $? -ne 0 && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `fix(test-reorg): replace assert True in test_init_coverage.py`
  - _Requirements: FR-8, AC-5.1, AC-5.4_

- [ ] 2.16 Fix assert True in test_init.py
  - **Do**: Find and replace `assert True` at line 830 in tests/integration/test_init.py. Examine the source code — comment says "Placeholder implementation - cleanup not yet active". If cleanup is now active (verify source), write real assertion. If not, remove the placeholder test.
  - **Files**: tests/integration/test_init.py (moved from tests/ in POC task 1.16)
  - **Done when**: `assert True` replaced or test removed; coverage stays 100%
  - **Verify**: `grep -n "assert True" tests/integration/test_init.py; test $? -ne 0 && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `fix(test-reorg): replace assert True in test_init.py`
  - _Requirements: FR-8, AC-5.2, AC-5.3_

- [ ] 2.17 [VERIFY] Quality checkpoint: assert True eliminated
  - **Do**: Verify zero `assert True` matches across all Python test files. Run `make test-cover`.
  - **Verify**: `grep -r "assert True" tests/unit/ tests/integration/ --include="*.py" | wc -l | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: 0 assert True violations; 100% coverage
  - **Commit**: None

- [ ] 2.18 Split conftest.py: extract root fixtures
  - **Do**: Identify the 8 truly shared fixtures (mock_datetime, mock_frame_reporting, vehicle_id, mock_store, sample_*_config, _make_mock_datetime_fixture, trip_manager_no_entry_id). Keep them in `tests/conftest.py`. Target ~120 LOC. Remove all integration-specific fixtures from root.
  - **Files**: tests/conftest.py
  - **Done when**: Root conftest.py has only shared fixtures; ~120 LOC
  - **Verify**: `wc -l tests/conftest.py | awk '{print $1}' | grep -q "^[0-9]\{2,3\}$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): trim root conftest.py to shared fixtures only`
  - _Requirements: FR-10, AC-7.1, AC-7.2_

- [ ] 2.19 Split conftest.py: create unit/conftest.py with unit fixtures
  - **Do**: Create `tests/unit/conftest.py` with `mock_hass` (minimal version) and `trip_manager_no_entry_id` fixtures. These are the unit-scoped fixtures that don't need HA framework.
  - **Files**: tests/unit/conftest.py
  - **Done when**: Unit conftest.py has mock_hass and trip_manager_no_entry_id; ~40 LOC
  - **Verify**: `grep -q "mock_hass" tests/unit/conftest.py && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): create unit conftest with mock_hass fixture`
  - _Requirements: FR-10, AC-7.3_

- [ ] 2.20 Split conftest.py: create integration/conftest.py with HA fixtures
  - **Do**: Create `tests/integration/conftest.py` with the remaining integration fixtures: hass (full mock), enable_custom_integrations, mock_input_text_*, mock_store_class, mock_entity/device_registry, mock_config_entries, mock_flow_manager, mock_er_async_get, mock_hass_with_entity_registry, trip_manager_with_entry_id. Target ~540 LOC.
  - **Files**: tests/integration/conftest.py
  - **Done when**: Integration conftest.py has all HA framework fixtures; tests pass
  - **Verify**: `grep -q "enable_custom_integrations" tests/integration/conftest.py && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): create integration conftest with HA framework fixtures`
  - _Requirements: FR-10, AC-7.3_

- [ ] 2.21 [VERIFY] Quality checkpoint: conftest split
  - **Do**: Run `make test` and `make test-cover`. Verify fixture resolution works across all layers.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All tests pass at 100%; no fixture resolution errors
  - **Commit**: None

- [ ] 2.22 Eliminate inline mock_hass in test_services_core.py (19 definitions)
  - **Do**: Replace all 19 inline `def mock_hass` definitions in `tests/integration/test_services_core.py` with usage of the conftest `mock_hass` or `hass` fixture. Remove duplicate definitions; ensure tests use the shared fixture.
  - **Files**: tests/integration/test_services_core.py
  - **Done when**: `grep -c "def mock_hass" tests/integration/test_services_core.py` returns 0
  - **Verify**: `grep -c "def mock_hass" tests/integration/test_services_core.py | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): eliminate inline mock_hass in test_services_core.py`
  - _Requirements: FR-11, AC-7.4_

- [ ] 2.23 Eliminate inline mock_hass in test_dashboard.py (10 definitions)
  - **Do**: Replace all 10 inline `def mock_hass` definitions in `tests/unit/test_dashboard.py` with usage of the conftest `mock_hass` fixture.
  - **Files**: tests/unit/test_dashboard.py
  - **Done when**: `grep -c "def mock_hass" tests/unit/test_dashboard.py` returns 0
  - **Verify**: `grep -c "def mock_hass" tests/unit/test_dashboard.py | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): eliminate inline mock_hass in test_dashboard.py`
  - _Requirements: FR-11, AC-7.4_

- [ ] 2.24 Eliminate inline mock_hass in test_init.py (4 definitions)
  - **Do**: Replace all 4 inline `def mock_hass` definitions in `tests/integration/test_init.py` with usage of conftest fixtures.
  - **Files**: tests/integration/test_init.py
  - **Done when**: `grep -c "def mock_hass" tests/integration/test_init.py` returns 0
  - **Verify**: `grep -c "def mock_hass" tests/integration/test_init.py | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): eliminate inline mock_hass in test_init.py`
  - _Requirements: FR-11, AC-7.4_

- [ ] 2.25 Eliminate inline mock_hass in remaining high-count files
  - **Do**: Replace inline `def mock_hass` in all remaining files that define it. NOTE: test_trip_manager.py and test_trip_manager_emhass.py were deleted in task 2.4 (consolidated). Use `grep -rl "def mock_hass" tests/unit/ tests/integration/ --include="*.py"` to find all remaining instances and replace with conftest fixtures. Expected files include: test_trip_crud.py, test_panel.py, test_yaml_trip_storage.py, test_migrate_entry.py, test_propagate_charge_integration.py, test_soc_cap_aggregation_ceil.py, test_charging_window.py, test_trip_manager_core.py (consolidated target), test_config_updates.py, test_presence_monitor_soc.py, test_soc_milestone.py, test_deferrable_load_sensors.py, test_entity_registry.py, test_functional_emhass_sensor_updates.py, test_full_user_journey.py, test_sensor_exists_fn.py, test_presence_monitor.py, test_sensor_coverage.py (or renamed test_sensor_integration.py), test_trip_calculations.py, test_emhass_adapter.py, test_user_real_data_simple.py, test_trip_manager_power_profile.py, and any others found by grep.
  - **Files**: ~24 test files in tests/unit/ and tests/integration/ (use grep to discover actual list)
  - **Done when**: `grep -rl "def mock_hass" tests/unit/ tests/integration/` returns 0 files
  - **Verify**: `grep -rl "def mock_hass" tests/unit/ tests/integration/ --include="*.py" | wc -l | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): eliminate all remaining inline mock_hass definitions`
  - _Requirements: FR-11, AC-7.4_

- [ ] 2.26 [VERIFY] Quality checkpoint: mock_hass elimination
  - **Do**: Run `make test` and `make test-cover`. Verify zero inline mock_hass remain.
  - **Verify**: `grep -rl "def mock_hass" tests/unit/ tests/integration/ --include="*.py" | wc -l | grep -q "^0$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: 0 inline mock_hass; 100% coverage
  - **Commit**: None

## Phase 3: Config Path Updates

Focus: Update all configuration files to reflect new test structure.

- [ ] 3.1 Update pyproject.toml testpaths and mutmut tests_dir
  - **Do**: Change `testpaths = ["tests"]` to `testpaths = ["tests/unit", "tests/integration"]`. Change `tests_dir = ["tests/"]` to `tests_dir = ["tests/unit/", "tests/integration/"]` in `[tool.mutmut]`.
  - **Files**: pyproject.toml
  - **Done when**: Both paths updated; `make test` discovers all tests
  - **Verify**: `grep -q '"tests/unit"' pyproject.toml && grep -q '"tests/integration"' pyproject.toml && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): update testpaths and mutmut tests_dir`
  - _Requirements: FR-18, FR-19, AC-11.1, AC-11.2_

- [ ] 3.2 Update Makefile test targets (7 targets)
  - **Do**: Update all `pytest tests` references in Makefile to `pytest tests/unit tests/integration`. Remove `--ignore=tests/e2e/` since e2e is no longer under the test path. Targets: test, test-cover, test-verbose, test-dashboard, test-parallel, test-random, htmlcov.
  - **Files**: Makefile
  - **Done when**: All 7 targets use new paths; `make test` passes
  - **Verify**: `grep -c "pytest tests/unit tests/integration" Makefile | grep -q "^[5-9]$" && make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
  - **Commit**: `refactor(test-reorg): update Makefile test paths to unit/ + integration/`
  - _Requirements: FR-20, AC-11.3_

- [ ] 3.3 [VERIFY] Quality checkpoint: Makefile targets work
  - **Do**: Run `make test`, `make test-cover`, `make test-verbose` (brief check). Verify all pass.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All Makefile targets pass at 100%
  - **Commit**: None

- [ ] 3.4 Update Makefile lint/dead-code/refurb paths
  - **Do**: Update `pylint custom_components/ tests/` to `pylint custom_components/ tests/unit/ tests/integration/`. Update `vulture custom_components/ tests/` to `vulture custom_components/ tests/unit/ tests/integration/`. Update `refurb custom_components/ tests/` to `refurb custom_components/ tests/unit/ tests/integration/`. Update `semgrep` path if it references tests/.
  - **Files**: Makefile
  - **Done when**: All quality tool paths updated; lint targets still work
  - **Verify**: `grep -q "tests/unit/" Makefile && grep -q "tests/integration/" Makefile && make lint 2>&1 | tail -3 && echo PASS`
  - **Commit**: `refactor(test-reorg): update lint/dead-code/refurb paths in Makefile`
  - _Requirements: AC-11.5_

- [ ] 3.5 Update .pre-commit-config.yaml and quality-gate scripts
  - **Do**: Verify `.pre-commit-config.yaml` works with new paths. Check quality-gate scripts (`.claude/skills/quality-gate/scripts/weak_test_detector.py`, `diversity_metric.py`) reference `tests/` — update to `tests/unit/` + `tests/integration/`.
  - **Files**: .pre-commit-config.yaml, .claude/skills/quality-gate/scripts/weak_test_detector.py, .claude/skills/quality-gate/scripts/diversity_metric.py
  - **Done when**: Pre-commit hooks work; quality-gate scripts target new paths
  - **Verify**: `grep -q "tests/unit" .claude/skills/quality-gate/scripts/weak_test_detector.py && echo PASS`
  - **Commit**: `refactor(test-reorg): update pre-commit and quality-gate script paths`
  - _Requirements: AC-11.5_

- [ ] 3.6 [VERIFY] Quality checkpoint: all config paths updated
  - **Do**: Run `make test`, `make test-cover`, `mutmut run --list` (verify file discovery). Verify pyright still excludes tests/.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo VERIFY_PASS`
  - **Done when**: All config paths correct; all tools discover tests
  - **Commit**: None

- [ ] 3.7 Document tests_excluded_from_mutmut disposition (files NOT moved — AC-12.3/12.4 not triggered)
  - **Do**: Add a comment in pyproject.toml near `[tool.mutmut]` documenting that `tests_excluded_from_mutmut/` (2 files) remain in their current location. Files are NOT being moved, so mutmut exclusion list does NOT need updating (AC-12.3/AC-12.4 condition "if files are moved" is false). Disposition of whether to integrate them into the new structure is deferred to Spec 5. Add note in `.progress.md`.
  - **Files**: pyproject.toml, specs/2-test-reorg/.progress.md
  - **Done when**: Comment in pyproject.toml documents deferral; progress.md updated; mutmut exclusion list unchanged
  - **Verify**: `grep -q "Spec 5" pyproject.toml && echo PASS`
  - **Commit**: `docs(test-reorg): document tests_excluded_from_mutmut disposition`
  - _Requirements: FR-25, AC-12.1, AC-12.2, AC-12.3 (not triggered — files not moved), AC-12.4 (not triggered)_

## Phase 4: Quality Gates

- [ ] 4.1 [VERIFY] Full local CI: make test + make test-cover + make lint
  - **Do**: Run `make test`, `make test-cover`, `make lint`. All must pass.
  - **Verify**: `make test-cover 2>&1 | tail -5 | grep -q "100%" && make lint 2>&1 | tail -1 && echo V4_PASS`
  - **Done when**: All local quality checks pass at 100%
  - **Commit**: None

- [ ] 4.2 Capture final metrics and compare with baseline
  - **Do**: Run `pytest --co -q` to get final test count. Compare with baseline in `specs/2-test-reorg/.baseline.txt`. Document delta in `.progress.md`.
  - **Files**: specs/2-test-reorg/.progress.md
  - **Done when**: Final metrics recorded; test count >= baseline; coverage = 100%
  - **Verify**: `grep -q "Final metrics" specs/2-test-reorg/.progress.md && echo PASS`
  - **Commit**: None

- [ ] 4.3 [VERIFY] VE1: E2E startup and run main suite
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Run `make e2e` which handles HA startup via scripts/run-e2e.sh
    2. Wait for completion
  - **Verify**: `make e2e 2>&1 | tail -20 | grep -q "passed" && echo VE1_PASS`
  - **Done when**: E2E tests pass on port 8123 (hass direct, NOT Docker)
  - **Commit**: None

- [ ] 4.4 [VERIFY] VE2: E2E SOC suite
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Run `make e2e-soc` which handles HA startup via scripts/run-e2e-soc.sh
    2. Wait for completion
  - **Verify**: `make e2e-soc 2>&1 | tail -20 | grep -q "passed" && echo VE2_PASS`
  - **Done when**: E2E SOC tests pass
  - **Commit**: None

- [ ] 4.5 [VERIFY] V5: Create PR
  - **Do**:
    1. Verify current branch: `git branch --show-current` (should be spec/2-test-reorg)
    2. Push branch: `git push -u origin spec/2-test-reorg`
    3. Create PR targeting epic/tech-debt-cleanup: `gh pr create --base epic/tech-debt-cleanup --title "refactor(tests): reorganize test architecture into unit/integration layers" --body "$(cat specs/2-test-reorg/.pr-body.md 2>/dev/null || echo 'Test architecture reorganization per spec 2-test-reorg')"`
  - **Verify**: `gh pr view --json url,state | jq -r '.state' | grep -q "OPEN" && echo V5_PASS`
  - **Done when**: PR exists on GitHub targeting epic/tech-debt-cleanup with state OPEN
  - **Commit**: None

- [ ] 4.6 [VERIFY] V6: AC checklist
  - **Do**: Programmatically verify each AC:
    - AC-1.1: `test -d tests/unit/ && echo PASS`
    - AC-1.2: `test -d tests/integration/ && echo PASS`
    - AC-1.3: `ls tests/e2e/*.spec.ts | wc -l | grep -q "^[0-9]" && echo PASS`
    - AC-1.4: `test -d tests/fixtures && echo PASS`
    - AC-1.5: `test -d tests/helpers && echo PASS`
    - AC-1.6: `make test 2>&1 | tail -3 | grep -q "passed" && echo PASS`
    - AC-1.7: `make test-cover 2>&1 | tail -5 | grep -q "100%" && echo PASS`
    - AC-2.1: `ls tests/unit/test_trip_manager*.py tests/integration/test_trip_manager*.py | wc -l | grep -q "^[3-5]$" && echo PASS`
    - AC-3.1: `ls tests/integration/test_config_flow*.py | wc -l | grep -q "^2$" && echo PASS`
    - AC-5.3: `grep -r "assert True" tests/unit/ tests/integration/ --include="*.py" | wc -l | grep -q "^0$" && echo PASS`
    - AC-7.1: `wc -l tests/conftest.py | awk '{print $1}' | grep -q "^[0-9]\{2,3\}$" && echo PASS` (root < 200 LOC)
    - AC-8.1-8.3: `.venv/bin/python -c "import time_machine; import hypothesis; import flake8_pytest_style" && echo PASS`
    - AC-9.1: `grep -q "strict = true" pyproject.toml && echo PASS`
    - AC-11.1: `grep -q '"tests/unit"' pyproject.toml && echo PASS`
  - **Verify**: All AC checks exit 0
  - **Done when**: All acceptance criteria confirmed met via automated checks
  - **Commit**: None

## Phase 5: PR Lifecycle

- [ ] 5.1 Monitor CI and address failures
  - **Do**: Check CI status. If failures found, read logs, fix locally, push fix.
  - **Verify**: `gh pr checks 2>&1 | grep -v "pending" | grep -v "skipped" | head -20`
  - **Done when**: CI checks pass or no CI configured for this branch
  - **Commit**: `fix(test-reorg): address CI failures` (if needed)

- [ ] 5.2 Resolve review comments
  - **Do**: If PR has review comments, address each one. Push fixes.
  - **Verify**: `gh pr view --json comments --jq '.comments | length' | grep -q "^0$" && echo NO_COMMENTS`
  - **Done when**: Zero unresolved review comments
  - **Commit**: `fix(test-reorg): address review feedback` (if needed)

## Notes

- **POC shortcuts taken**: None — each phase is verified at 100% coverage
- **Production TODOs**:
  - Spec 5 (Mutation Ramp): Improve mutation scores using new test structure
  - Spec 6 (Coverage Gap): Eliminate 118 `pragma: no cover` lines
  - Spec 7 (Lint/Format/Type): Enforce flake8-pytest-style on new file locations
  - Future: Apply `@pytest.mark.unit` / `@pytest.mark.integration` markers to all tests
  - Future: Add `spec=` to all MagicMock instances (quality improvement)
  - Future: Per-module subdirectories under tests/unit/ (optional)
- **E2E tests**: Unchanged (TypeScript, port 8123, hass direct)
- **panel.test.js**: Stays in tests/ root (Jest, not Playwright)
- **tests_excluded_from_mutmut/**: Disposition deferred to Spec 5
