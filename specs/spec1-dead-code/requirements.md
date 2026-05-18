# Requirements: Dead Code & Artifact Elimination

## Goal

Remove all dead code, backup files, and stale artifacts from the codebase to reduce source LOC without changing any runtime behavior -- every deletion must pass the full test suite.

## User Stories

### US-1: Dead Module Removal
**As a** developer maintaining the codebase
**I want to** remove the unused `schedule_monitor` module and its test suite
**So that** the codebase contains only modules that are actively wired into the integration

**Acceptance Criteria:**
- [ ] AC-1.1: `custom_components/ev_trip_planner/schedule_monitor.py` deleted (327 LOC)
- [ ] AC-1.2: `tests/test_schedule_monitor.py` deleted (33 tests)
- [ ] AC-1.3: `tests/test_coverage_edge_cases.py` updated -- remove `test_schedule_monitor_notify_with_none_service` (lines 522-548)
- [ ] AC-1.10: `[tool.quality-gate.mutation.modules.schedule_monitor]` section removed from `pyproject.toml` (lines 155-157)

### US-2: Tracked Artifact Cleanup
**As a** developer
**I want to** untrack stale `.py,cover` files that are already gitignored
**So that** the repository no longer tracks mutmut coverage artifacts

**Acceptance Criteria:**
- [ ] AC-1.4: `git rm --cached` for all 19 tracked `*,cover` files (pattern already in `.gitignore`)
- [ ] AC-1.11: `protocols.py,cover` removed (orphaned -- `protocols.py` does not exist as source)

### US-3: E2E Config Relocation & Ha-Manual Deletion
**As a** developer
**I want to** relocate the E2E configuration file and delete the unused `tests/ha-manual/` directory
**So that** 195 MB of unused HA test instance data is removed without breaking E2E scripts

**Acceptance Criteria:**
- [ ] AC-1.12 (pre-step): `tests/ha-manual/configuration.yaml` relocated to `scripts/e2e-config/configuration.yaml`
- [ ] AC-1.12a: `scripts/run-e2e.sh:93` updated to reference `scripts/e2e-config/configuration.yaml`
- [ ] AC-1.12b: `scripts/run-e2e-soc.sh:85` updated to reference `scripts/e2e-config/configuration.yaml`
- [ ] AC-1.12c: `.github/workflows/playwright.yml.disabled:41` updated to reference `scripts/e2e-config/configuration.yaml`
- [ ] AC-1.12d: `tests/ha-manual/` directory deleted (195 MB, 30 items)
- [ ] AC-1.16: `--ignore=tests/ha-manual/` removed from 6 Makefile targets (lines 66, 69, 72, 75, 271, 275)

### US-4: Dead Constants Removal
**As a** developer
**I want to** remove constants that have zero references anywhere in the codebase
**So that** the codebase has no unused definitions

**Acceptance Criteria:**
- [ ] AC-1.14: `SIGNAL_TRIPS_UPDATED` (const.py:21), `DEFAULT_CONTROL_TYPE` (const.py:67), `DEFAULT_NOTIFICATION_SERVICE` (const.py:71) deleted
- [ ] AC-1.14b: `ALL_DAYS` (utils.py:34) deleted (parent `DAY_ABBREVIATIONS` remains active)

### US-5: Orphaned File Cleanup
**As a** developer
**I want to** remove orphaned backup files
**So that** no stale editor or tool artifacts remain

**Acceptance Criteria:**
- [ ] AC-1.15: `.qwen/settings.json.orig` deleted

### US-6: Verification & Safety
**As a** developer
**I want to** verify all deletions pass the full test suite
**So that** no runtime behavior is affected by cleanup

**Acceptance Criteria:**
- [ ] AC-1.8: `make test` passes with ~1,815 tests (baseline 1,849 minus 34 removed)
- [ ] AC-1.8b: `make test-cover` passes
- [ ] AC-1.8c: `make e2e` passes
- [ ] AC-1.8d: `make e2e-soc` passes
- [ ] AC-1.9: `ruff check --select F401` passes clean (no new import errors)
- [ ] AC-1.13: Verify `async_import_dashboard_for_entry` is standard HA pattern via tests -- if confirmed, NO-OP

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Delete `schedule_monitor.py` and its test suite | High | File absent, `grep -rn schedule_monitor custom_components/` empty |
| FR-2 | Untrack 19 `*,cover` files from git | High | `git ls-files '*.py,cover'` returns empty |
| FR-3 | Relocate E2E config before ha-manual deletion | High | `scripts/e2e-config/configuration.yaml` exists, E2E scripts reference it |
| FR-4 | Delete `tests/ha-manual/` directory | High | Directory absent, `ls tests/ha-manual/` fails |
| FR-5 | Remove `--ignore=tests/ha-manual/` from Makefile | Medium | `grep "ha-manual" Makefile` returns empty |
| FR-6 | Delete dead constants in const.py and utils.py | Medium | `grep -rn "SIGNAL_TRIPS_UPDATED\|DEFAULT_CONTROL_TYPE\|DEFAULT_NOTIFICATION_SERVICE\|ALL_DAYS" custom_components/` returns empty |
| FR-7 | Delete `.qwen/settings.json.orig` | Low | File absent |
| FR-8 | Remove schedule_monitor mutation config from pyproject.toml | Medium | `grep "schedule_monitor" pyproject.toml` returns empty |
| FR-9 | Surgical removal of 1 test from `test_coverage_edge_cases.py` | High | File still exists, lines 522-548 removed, file passes Python syntax check |
| FR-10 | Full test suite passes after all deletions | High | `make test && make e2e && make e2e-soc` exit 0 |
| FR-11 | Dead code detection passes clean | High | `make dead-code` (vulture --min-confidence 80) exits 0 with zero findings. Iterate: detect → fix/configure → confirm → re-configure if false positives appear |
| FR-12 | Full quality gate baseline captured BEFORE changes | High | `make quality-gate` runs and outputs saved to `_bmad-output/quality-gate/spec1-baseline/`. All layer results recorded |
| FR-13 | Full quality gate validation AFTER changes — metrics cannot regress | High | `make quality-gate` runs post-implementation. Every layer metric must be equal or better than baseline: test count, coverage %, mutation scores, lint errors, SOLID violations, security findings |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Zero behavior change | All test suites pass | 1,815+ tests green, 0 failures |
| NFR-2 | No import regressions | ruff F401 check | 0 unused import warnings |
| NFR-3 | Repository size reduction | `tests/ha-manual/` removal | ~195 MB freed |
| NFR-4 | Source LOC reduction | Lines removed | ~660 LOC source + 898 LOC tests removed (871 test_schedule_monitor.py + 27 lines from test_coverage_edge_cases.py) |
| NFR-5 | Quality gate non-regression | All quality gate metrics | Post-implementation quality gate cannot be worse than baseline on ANY layer |
| NFR-6 | Dead code tooling confidence | vulture false-positive rate | Zero false positives at min-confidence 80 — configure whitelist if needed |

## Implementation Constraints

**Mandatory order** (blocker-enforced):

0. **QUALITY GATE BASELINE**: Run `make quality-gate` and save full output to `_bmad-output/quality-gate/spec1-baseline/`. This is the pre-implementation snapshot.
1. **PRE-STEP** (blocker for AC-1.12): Create `scripts/e2e-config/configuration.yaml` from `tests/ha-manual/configuration.yaml`. Update `scripts/run-e2e.sh:93`, `scripts/run-e2e-soc.sh:85`, `.github/workflows/playwright.yml.disabled:41`.
2. `git rm --cached` for 19 `.cover` files.
3. Delete `schedule_monitor.py` + `test_schedule_monitor.py` + update `test_coverage_edge_cases.py`.
4. Delete `tests/ha-manual/` (safe after pre-step).
5. Update `pyproject.toml` mutation config.
6. Delete dead constants from `const.py` and `utils.py`.
7. Delete `.qwen/settings.json.orig`.
8. Remove `--ignore=tests/ha-manual/` from Makefile (6 targets).
9. Verify AC-1.13 (`async_import_dashboard_for_entry` -- confirm NO-OP).
10. Run `make test`, `make e2e`, `make e2e-soc` -- all must pass.
11. Run `make dead-code` (vulture) -- must pass clean. If false positives, configure whitelist and iterate until clean.
12. Run `make lint && make typecheck` -- final validation.
13. **QUALITY GATE VALIDATION**: Run `make quality-gate`. Compare against baseline. Every layer must be equal or better.
14. Update 6 documentation files referencing schedule_monitor (optional, non-blocking).

## Glossary

- **schedule_monitor.py**: Dead module (327 LOC) with zero production imports, not registered as HA platform, not in manifest.json
- ***,cover files**: mutmut mutation testing coverage artifacts -- already gitignored but still git-tracked
- **tests/ha-manual/**: Full HA test instance directory (195 MB) used historically for manual testing, not used by any active CI or quality gate
- **Dead constants**: `SIGNAL_TRIPS_UPDATED`, `DEFAULT_CONTROL_TYPE`, `DEFAULT_NOTIFICATION_SERVICE` (const.py), `ALL_DAYS` (utils.py) -- zero references in any file type
- **async_import_dashboard_for_entry**: Active function in services.py that auto-imports Lovelace dashboard on vehicle setup -- standard HA pattern, NOT deprecated
- **NO-OP**: No operation required -- the item requires no code change

## Out of Scope

- `dashboard.py` and `vehicle_controller.py` -- confirmed active, god class targets for Spec 3
- Dead methods in live modules (emhass_adapter, presence_monitor, panel, vehicle_controller, trip_manager) -- Spec 5 scope
- `mutants/` directory -- already gitignored (line 111 of .gitignore), no action needed
- Adding feature flag for dashboard auto-import -- deferred to Spec 3 or future spec
- Documentation updates for schedule_monitor references (6 files) -- recommended but non-blocking
- `mock_schedule_monitor` fixture in `test_init.py:569` -- orphaned mock name, not an import, no action needed
- Any behavior change, refactoring, or new functionality
- SOLID compliance improvements, test quality improvements, coverage improvements

## Dependencies

- **Spec 0 (Tooling Foundation)**: COMPLETED -- provides vulture, deptry, quality gate infrastructure used in research
- **Spec 3 (Solid Refactor)**: Downstream -- receives dashboard.py and vehicle_controller.py as god class targets
- **Spec 5 (Mutation)**: Downstream -- receives list of dead methods in live modules for mutation-driven validation

## Success Criteria

- `make quality-gate` baseline saved to `_bmad-output/quality-gate/spec1-baseline/` BEFORE any changes
- `make test` passes with ~1,815 tests (0 failures)
- `make e2e` and `make e2e-soc` pass (0 failures)
- `make dead-code` passes clean (vulture, zero findings at min-confidence 80)
- `git ls-files '*.py,cover'` returns empty
- `grep -rn schedule_monitor custom_components/` returns empty
- `ls tests/ha-manual/` returns error (directory gone)
- `grep -rn "SIGNAL_TRIPS_UPDATED\|DEFAULT_CONTROL_TYPE\|DEFAULT_NOTIFICATION_SERVICE\|ALL_DAYS" custom_components/` returns empty
- Repository size reduced by ~195 MB (ha-manual deletion)
- Source LOC reduced by ~660 lines (schedule_monitor + constants)
- Test LOC reduced by ~898 lines (test_schedule_monitor + 1 test)
- **Post-implementation quality gate is equal or better than baseline on every layer**

## Verification Contract

**Project type**: fullstack

**Entry points**:
- `make test` (pytest, ~1,815 tests after cleanup)
- `make test-cover` (coverage report)
- `make e2e` (Playwright E2E suite against HA on :8123)
- `make e2e-soc` (Playwright dynamic SOC suite against HA on :8123)
- `scripts/run-e2e.sh` (references relocated `scripts/e2e-config/configuration.yaml`)
- `scripts/run-e2e-soc.sh` (references relocated `scripts/e2e-config/configuration.yaml`)
- `ruff check --select F401` (import validation)
- `make lint && make typecheck` (final validation)

**Observable signals**:
- PASS looks like: `make test` exits 0 with `1815 passed`, `make e2e` exits 0 with all specs passing, `git status` shows files deleted/untracked, `git ls-files '*.py,cover'` returns empty
- FAIL looks like: `ModuleNotFoundError: No module named 'schedule_monitor'` (leftover import), `make e2e` fails with `cp: cannot stat 'tests/ha-manual/configuration.yaml'` (missed relocation), `ruff` reports unused imports, `make test` reports failures

**Hard invariants**:
- `async_import_dashboard_for_entry` must remain functional (called from `__init__.py:201` during vehicle setup)
- `dashboard.py` must remain untouched (3 active importers)
- `vehicle_controller.py` must remain untouched (14 references across 4 files)
- `conf.py` active constants (`CONF_NOTIFICATION_SERVICE`, `CONF_VEHICLE_NAME`, `DAY_ABBREVIATIONS`) must not be affected
- E2E scripts must find configuration.yaml at new location after relocation
- `protocols.py` does NOT exist as source -- do not attempt to create it

**Seed data**:
- Python venv activated (`. .venv/bin/activate`)
- Current test baseline: 1,849 tests passing
- `tests/ha-manual/configuration.yaml` exists (62 lines, minimal HA config for E2E)
- 19 `*,cover` files are git-tracked despite being gitignored
- `scripts/e2e-config/` directory must be created as part of implementation

**Dependency map**:
- `scripts/run-e2e.sh` -- shares config path with `tests/ha-manual/configuration.yaml`
- `scripts/run-e2e-soc.sh` -- shares config path with `tests/ha-manual/configuration.yaml`
- `Makefile` -- 6 test targets reference `tests/ha-manual/` via `--ignore` flags
- `pyproject.toml` -- mutation config references schedule_monitor module
- `custom_components/ev_trip_planner/const.py` -- shared constants file (only dead constants removed)
- `custom_components/ev_trip_planner/utils.py` -- shared utilities file (only `ALL_DAYS` removed)
- `.github/workflows/playwright.yml.disabled` -- references old config path (disabled but must update)

**Escalate if**:
- `make test` shows ANY unexpected test failure (not just the 34 removed tests)
- `make e2e` or `make e2e-soc` fails after configuration.yaml relocation
- Any import error appears in `ruff check --select F401` or `make lint`
- `grep` finds any reference to `schedule_monitor` in production code that was missed during research
- Dead constants have gained references since research (re-verify before deletion)
- `protocols.py` source file is found to exist (would mean `protocols.py,cover` is not orphaned)

## Unresolved Questions

- AC-1.13: `async_import_dashboard_for_entry` -- research says NO-OP (standard HA pattern, actively tested). Agent will verify hypothesis via tests. If confirmed, no action taken. If not confirmed, escalate.
- ~~Documentation updates: 6 docs files reference schedule_monitor.~~ **RESOLVED**: design.md Technical Decisions table confirms "During implementation". Included as Task 4.2.

## Next Steps

1. User approves requirements
2. Design phase creates implementation plan with exact file paths and line numbers
3. Implementation follows mandatory order (blocker pre-step first)
4. Verification runs `make test && make e2e && make e2e-soc` after all deletions

## Traceability: Spec ACs → Epic ACs

| Spec AC | Epic AC | Notes |
|---------|---------|-------|
| AC-1.1 | AC-1.1 | Delete schedule_monitor.py |
| AC-1.2 | AC-1.2 | Delete test_schedule_monitor.py |
| AC-1.3 | AC-1.3 | Update test_coverage_edge_cases.py |
| AC-1.10 | AC-1.10 | Remove mutation config from pyproject.toml |
| AC-1.4 | AC-1.4 + AC-1.11 | Untrack .cover files (includes orphaned protocols.py,cover) |
| AC-1.5 | AC-1.5 | NO-OP -- frontend backups already removed |
| AC-1.6, AC-1.7 | AC-1.6, AC-1.7 | Verify dashboard.py and vehicle_controller.py remain |
| AC-1.12a-d | AC-1.12 | Config relocation + ha-manual deletion (spec decomposes epic AC into steps) |
| AC-1.16 | AC-1.16 (new) | Remove Makefile --ignore flags |
| AC-1.14, AC-1.14b | AC-1.14 (new) | Dead constants removal |
| AC-1.15 | AC-1.15 (new) | Delete .qwen/settings.json.orig |
| AC-1.8, AC-1.8b-d | AC-1.8 | Test suite passes (epic estimated ~1,830; research confirms ~1,815) |
| AC-1.9 | AC-1.9 | No new import errors |
| AC-1.13 | AC-1.13 | Verify auto-import is active (NOT deprecated per research) |
