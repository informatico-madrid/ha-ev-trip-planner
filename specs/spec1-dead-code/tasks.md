# Tasks: Dead Code & Artifact Elimination

## Phase 1: Make It Work (POC)

Focus: Execute all deletions in blocker-enforced order. Skip test writing (pure deletion spec). Validate via existing test suite.

- [x] 1.1 Quality gate baseline capture
  - **Do**:
    1. Create baseline directory: `mkdir -p _bmad-output/quality-gate/spec1-baseline/`
    2. Activate venv and run: `make quality-gate 2>&1 | tee _bmad-output/quality-gate/spec1-baseline/output.txt`
    3. Record baseline test count (1,849), coverage %, mutation scores from output
    4. Capture baseline commit hash: `BASELINE_SHA=$(git rev-parse HEAD) && echo "Baseline: $BASELINE_SHA"`
  - **Files**: `_bmad-output/quality-gate/spec1-baseline/output.txt` (CREATE)
  - **Done when**: Quality gate output saved, baseline metrics recorded in .progress.md
  - **Verify**: `test -f _bmad-output/quality-gate/spec1-baseline/output.txt && echo BASELINE_CAPTURED`
  - **Commit**: `chore(spec1): capture quality gate baseline before dead code cleanup`
  - _Requirements: FR-12_

- [ ] 1.2 BLOCKER: E2E config relocation -- copy configuration.yaml and update 3 script references
  - **Do**:
    1. Create target: `mkdir -p scripts/e2e-config/`
    2. Copy: `cp tests/ha-manual/configuration.yaml scripts/e2e-config/configuration.yaml`
    3. Update `scripts/run-e2e.sh:93` -- replace `tests/ha-manual/configuration.yaml` with `scripts/e2e-config/configuration.yaml`
    4. Update `scripts/run-e2e-soc.sh:85` -- replace `tests/ha-manual/configuration.yaml` with `scripts/e2e-config/configuration.yaml`
    5. Update `.github/workflows/playwright.yml.disabled:41` -- replace `tests/ha-manual/configuration.yaml` with `scripts/e2e-config/configuration.yaml`
    6. Stage new file: `git add scripts/e2e-config/configuration.yaml`
  - **Files**: `scripts/e2e-config/configuration.yaml` (CREATE), `scripts/run-e2e.sh` (MODIFY), `scripts/run-e2e-soc.sh` (MODIFY), `.github/workflows/playwright.yml.disabled` (MODIFY)
  - **Done when**: New config file exists, `grep -rn "tests/ha-manual/configuration.yaml" scripts/ .github/` returns empty
  - **Verify**: `test -f scripts/e2e-config/configuration.yaml && ! grep -rn "tests/ha-manual/configuration.yaml" scripts/ .github/ && echo RELOCATE_PASS`
  - **Commit**: `refactor(e2e): relocate configuration.yaml from tests/ha-manual to scripts/e2e-config`
  - _Requirements: FR-3, AC-1.12, AC-1.12a, AC-1.12b, AC-1.12c_

- [ ] 1.3 [P] Untrack 19 .cover files from git and remove from disk
  - **Do**:
    1. Verify .gitignore pattern exists: `grep ',cover' .gitignore` (must match at line 30)
    2. Run `git rm --cached $(git ls-files '*.py,cover')` to untrack all 19 mutmut coverage artifacts
    3. Remove from disk: `rm -f custom_components/ev_trip_planner/*.py,cover`
  - **Files**: 19 `*.py,cover` files (GIT RM --CACHED + DELETE from disk)
  - **Done when**: `git ls-files '*.py,cover'` returns empty AND files removed from disk
  - **Verify**: `git ls-files '*.py,cover' | wc -l | grep -q '^0$' && echo UNTRACK_PASS`
  - **Commit**: `chore(cleanup): untrack and remove 19 mutmut .cover files`
  - _Requirements: FR-2, AC-1.4, AC-1.11_

- [ ] 1.4 [P] Delete schedule_monitor module, test file, coverage edge case test, and mutation config
  - **Do**:
    1. Delete: `rm custom_components/ev_trip_planner/schedule_monitor.py`
    2. Delete: `rm tests/test_schedule_monitor.py`
    3. Delete disk cover: `rm -f custom_components/ev_trip_planner/schedule_monitor.py,cover`
    4. Edit `tests/test_coverage_edge_cases.py` -- remove lines 522-548 (section header + `test_schedule_monitor_notify_with_none_service`)
    5. Edit `pyproject.toml` -- remove lines 155-157 (`[tool.quality-gate.mutation.modules.schedule_monitor]` section)
  - **Files**: `custom_components/ev_trip_planner/schedule_monitor.py` (DELETE), `tests/test_schedule_monitor.py` (DELETE), `tests/test_coverage_edge_cases.py` (MODIFY), `pyproject.toml` (MODIFY)
  - **Done when**: Schedule_monitor files gone, pyproject.toml has no schedule_monitor reference, test file edited
  - **Verify**: `! test -f custom_components/ev_trip_planner/schedule_monitor.py && ! grep -q "schedule_monitor" pyproject.toml && echo DELETE_SM_PASS`
  - **Commit**: `refactor(cleanup): delete schedule_monitor module, tests, and mutation config`
  - _Requirements: FR-1, FR-8, FR-9, AC-1.1, AC-1.2, AC-1.3, AC-1.10_

- [ ] 1.5 Delete tests/ha-manual/ directory (195 MB)
  - **Do**:
    1. Run `rm -rf tests/ha-manual/`
  - **Files**: `tests/ha-manual/` (DELETE entire directory)
  - **Done when**: `ls tests/ha-manual/` returns error (directory gone)
  - **Verify**: `! test -d tests/ha-manual && echo HA_MANUAL_GONE`
  - **Commit**: `chore(cleanup): delete tests/ha-manual directory (195 MB)`
  - _Requirements: FR-4, AC-1.12d_
  - _Design: Step 4 -- safe after config relocation in 1.2_

- [ ] 1.6 [P] Delete dead constants from const.py and utils.py
  - **Do**:
    1. Re-verify zero references: `grep -rn "SIGNAL_TRIPS_UPDATED\|DEFAULT_CONTROL_TYPE\|DEFAULT_NOTIFICATION_SERVICE\|ALL_DAYS" custom_components/ tests/ --include="*.py"` -- must return ONLY definition lines (NOTE: valid only after task 1.5 deletes tests/ha-manual/ which contains copies of const.py)
    2. Edit `custom_components/ev_trip_planner/const.py` -- remove `SIGNAL_TRIPS_UPDATED` (line 21-22), `DEFAULT_CONTROL_TYPE` (line 67), `DEFAULT_NOTIFICATION_SERVICE` (line 71)
    3. Edit `custom_components/ev_trip_planner/utils.py` -- remove `ALL_DAYS = set(DAY_ABBREVIATIONS.keys())` (line 34) + adjacent blank line if double-blank results
  - **Files**: `custom_components/ev_trip_planner/const.py` (MODIFY), `custom_components/ev_trip_planner/utils.py` (MODIFY)
  - **Done when**: `grep -rn "SIGNAL_TRIPS_UPDATED\|DEFAULT_CONTROL_TYPE\|DEFAULT_NOTIFICATION_SERVICE\|ALL_DAYS" custom_components/ --include="*.py"` returns empty
  - **Verify**: `! grep -rn "SIGNAL_TRIPS_UPDATED\|DEFAULT_CONTROL_TYPE\|DEFAULT_NOTIFICATION_SERVICE\|ALL_DAYS" custom_components/ --include="*.py" && echo CONSTANTS_GONE`
  - **Commit**: `refactor(cleanup): remove 4 dead constants (const.py, utils.py)`
  - _Requirements: FR-6, AC-1.14, AC-1.14b_

- [ ] 1.7 [P] Delete .qwen/settings.json.orig and clean Makefile --ignore flags
  - **Do**:
    1. Delete: `rm .qwen/settings.json.orig`
    2. Edit `Makefile` -- remove `--ignore=tests/ha-manual/` from 6 targets: test (line 66), test-cover (69), test-verbose (72), test-dashboard (75), test-parallel (271), test-random (275)
  - **Files**: `.qwen/settings.json.orig` (DELETE), `Makefile` (MODIFY)
  - **Done when**: `.qwen/settings.json.orig` absent, `grep "ha-manual" Makefile` returns empty
  - **Verify**: `! test -f .qwen/settings.json.orig && ! grep -q "ha-manual" Makefile && echo CLEANUP_PASS`
  - **Commit**: `chore(cleanup): delete .qwen backup and remove Makefile ha-manual ignore flags`
  - _Requirements: FR-5, FR-7, AC-1.15, AC-1.16_

- [ ] 1.8 V1 [VERIFY] Quality checkpoint: verify no import regressions after all deletions
  - **Do**: Run lint and unused import checks to confirm no breakage from deletions
  - **Verify**: `make lint && ruff check --select F401 custom_components/ tests/ && echo V1_PASS`
  - **Done when**: Zero lint errors, zero unused import warnings
  - **Commit**: `chore(spec1): pass quality checkpoint after deletions` (only if fixes needed)

- [ ] 1.9 Verify AC-1.13 NO-OP and run full test suite
  - **Do**:
    1. Verify `async_import_dashboard_for_entry` is active: `grep -rn "async_import_dashboard_for_entry" custom_components/ tests/ --include="*.py" | head -10`
    2. Activate venv: `. .venv/bin/activate`
    3. Run `make test` -- expect ~1,815 tests (34 fewer than baseline 1,849)
    4. Run `make test-cover` -- coverage report should still pass
  - **Files**: None (verification only)
  - **Done when**: `make test` exits 0 with ~1,815 tests, `make test-cover` exits 0, `async_import_dashboard_for_entry` confirmed active in >= 4 locations
  - **Verify**: `. .venv/bin/activate && make test 2>&1 | tail -5 && echo TEST_PASS`
  - **Commit**: None (verification task -- no code changes)
  - _Requirements: FR-10, AC-1.8, AC-1.8b, AC-1.13_

- [ ] 1.10 POC Checkpoint: run E2E tests to verify config relocation worked
  - **Do**:
    1. Activate venv: `. .venv/bin/activate`
    2. Run `make e2e` -- all Playwright specs against :8123 must pass
    3. Run `make e2e-soc` -- all SOC specs must pass
  - **Files**: None (verification only)
  - **Done when**: `make e2e` and `make e2e-soc` both exit 0
  - **Verify**: `. .venv/bin/activate && make e2e 2>&1 | tail -5 && echo E2E_PASS`
  - **Commit**: None (verification checkpoint)
  - _Requirements: FR-10, AC-1.8c, AC-1.8d_
  - _Design: Steps 8-9 -- confirms config relocation and all deletions are safe_

## Phase 2: Refactoring

No code refactoring needed for this pure-deletion spec. All changes are mechanical deletions.

## Phase 3: Testing

No new tests to write. This spec is pure deletion -- verification is via existing test suite (Phase 1).

## Phase 4: Quality Gates

- [ ] V2 [VERIFY] Dead code detection: vulture passes clean
  - **Do**: Run `make dead-code` (vulture --min-confidence 80). If false positives, add to vulture whitelist in pyproject.toml and iterate.
  - **Verify**: `. .venv/bin/activate && make dead-code && echo V2_PASS`
  - **Done when**: vulture exits 0 with zero findings at min-confidence 80
  - **Commit**: `chore(spec1): configure vulture whitelist if needed` (only if false positives found)
  - _Requirements: FR-11, AC-1.11, NFR-6_

- [ ] V3 [VERIFY] Full lint + typecheck validation
  - **Do**: Run `make lint && make typecheck`
  - **Verify**: `. .venv/bin/activate && make lint && make typecheck && echo V3_PASS`
  - **Done when**: Both commands exit 0
  - **Commit**: `chore(spec1): fix lint/typecheck issues if any` (only if fixes needed)

- [ ] 4.1 Quality gate validation vs baseline
  - **Do**:
    1. Create validation dir: `mkdir -p _bmad-output/quality-gate/spec1-validation/`
    2. Run `make quality-gate 2>&1 | tee _bmad-output/quality-gate/spec1-validation/output.txt`
    3. Compare layer-by-layer against baseline in `_bmad-output/quality-gate/spec1-baseline/output.txt`
    4. Every metric must be equal or better: test count, coverage %, mutation scores, lint, security
  - **Files**: `_bmad-output/quality-gate/spec1-validation/output.txt` (CREATE)
  - **Done when**: Quality gate passes and no layer regressed vs baseline
  - **Verify**: `test -f _bmad-output/quality-gate/spec1-validation/output.txt && echo QG_VALIDATED`
  - **Commit**: `chore(spec1): quality gate validation passed`
  - _Requirements: FR-13, NFR-5_

- [ ] 4.2 Update 6 documentation files referencing schedule_monitor
  - **Do**: Remove schedule_monitor references from:
    1. `docs/architecture.md:171` -- remove section 11 describing schedule_monitor.py module
    2. `docs/source-tree-analysis.md:24,64` -- remove tree entries for schedule_monitor.py and its tests
    3. `docs/development-guide.md:131` -- remove tree entry for schedule_monitor.py
    4. `docs/MILESTONE_4_POWER_PROFILE.md:279` -- update schedule_monitor reference
    5. `docs/MILESTONE_4_1_PLANNING.md:22,285` -- update schedule_monitor reference (line 22) and Wire ScheduleMonitor task in table (line 285)
    6. `docs/DOCS_DEEP_AUDIT.md:99,132` -- remove audit entries listing schedule_monitor
  - **Files**: `docs/architecture.md`, `docs/source-tree-analysis.md`, `docs/development-guide.md`, `docs/MILESTONE_4_POWER_PROFILE.md`, `docs/MILESTONE_4_1_PLANNING.md`, `docs/DOCS_DEEP_AUDIT.md`
  - **Done when**: `grep -rn "schedule_monitor" docs/` returns empty
  - **Verify**: `! grep -rn "schedule_monitor" docs/ && echo DOCS_CLEAN`
  - **Commit**: `docs(cleanup): remove schedule_monitor references from 6 documentation files`

- [ ] V4 [VERIFY] Full local CI: lint + typecheck + test + dead-code
  - **Do**: Run complete local CI suite
  - **Verify**: `. .venv/bin/activate && make lint && make typecheck && make test && make dead-code && echo V4_PASS`
  - **Done when**: All commands exit 0
  - **Commit**: `chore(spec1): pass full local CI` (only if fixes needed)

- [ ] V5 [VERIFY] PR opened correctly
  - **Do**:
    1. Verify current branch is feature branch: `git branch --show-current`
    2. Push branch: `git push -u origin $(git branch --show-current)`
    3. Create PR: `gh pr create --title "refactor: dead code & artifact elimination (Spec 1)" --body "$(cat <<'EOF'
## Summary
- Delete schedule_monitor module (327 LOC) + tests (871 LOC, 33 tests)
- Untrack 19 mutmut .cover files from git
- Relocate E2E configuration.yaml from tests/ha-manual/ to scripts/e2e-config/
- Delete tests/ha-manual/ directory (195 MB)
- Remove 4 dead constants (const.py, utils.py)
- Delete .qwen/settings.json.orig orphaned backup
- Clean Makefile --ignore flags (6 targets)
- Update 6 documentation files

## Test plan
* make test passes (~1,815 tests, 34 fewer than baseline)
* make e2e and make e2e-soc pass
* make dead-code (vulture) passes clean
* make lint && make typecheck pass
* Quality gate non-regression vs baseline

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"`
  - **Verify**: `gh pr view --json url,state | jq -r '.state' | grep -q OPEN && echo V5_PASS`
  - **Done when**: PR exists on GitHub with state OPEN
  - **Commit**: None

- [ ] V6 [VERIFY] AC checklist: programmatically verify all 16 acceptance criteria
  - **Do**: Run automated checks for each AC:
    1. AC-1.1: `! test -f custom_components/ev_trip_planner/schedule_monitor.py`
    2. AC-1.2: `! test -f tests/test_schedule_monitor.py`
    3. AC-1.3: `! grep -q "schedule_monitor" tests/test_coverage_edge_cases.py`
    4. AC-1.4: `git ls-files '*.py,cover' | wc -l` returns 0
    5. AC-1.5: SKIP (already done)
    6. AC-1.6: `test -f custom_components/ev_trip_planner/dashboard.py` (remains)
    7. AC-1.7: `test -f custom_components/ev_trip_planner/vehicle_controller.py` (remains)
    8. AC-1.8: `make test` exits 0
    9. AC-1.9: `ruff check --select F401 custom_components/` exits 0
    10. AC-1.10: `! grep -q "schedule_monitor" pyproject.toml`
    11. AC-1.11: `! git ls-files '*.py,cover' | grep -q protocols`
    12. AC-1.12: `test -f scripts/e2e-config/configuration.yaml && ! test -d tests/ha-manual`
    13. AC-1.13: `grep -q "async_import_dashboard_for_entry" custom_components/ev_trip_planner/services.py` (remains)
    14. AC-1.14: `! grep -rn "SIGNAL_TRIPS_UPDATED\|DEFAULT_CONTROL_TYPE\|DEFAULT_NOTIFICATION_SERVICE" custom_components/ev_trip_planner/const.py`
    15. AC-1.15: `! test -f .qwen/settings.json.orig`
    16. AC-1.16: `! grep -q "ha-manual" Makefile`
  - **Verify**: All 16 checks pass (echo AC_ALL_PASS)
  - **Done when**: Every AC confirmed met via automated grep/test
  - **Commit**: None

- [ ] VE0 [VERIFY] UI Map Init: build selector map for E2E verification
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**: Load `ui-map-init` skill and follow VE0 protocol. Build `ui-map.local.md` with selectors for the EV Trip Planner panel in Home Assistant.
  - **Verify**: `test -f specs/spec1-dead-code/ui-map.local.md && grep -c '|' specs/spec1-dead-code/ui-map.local.md | grep -qv '^0$' && echo VE0_PASS`
  - **Done when**: Map written (or confirmed current), session closed
  - **Commit**: None

- [ ] VE1 [VERIFY] E2E startup: start HA E2E test instance and wait for ready
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Start HA E2E instance: `scripts/run-e2e.sh &` (uses relocated `scripts/e2e-config/configuration.yaml`)
    2. Record PID: `echo $! > /tmp/ve-pids.txt`
    3. Wait for HA ready on :8123 with 90s timeout: `for i in $(seq 1 90); do curl -sf http://localhost:8123/api/ && break || sleep 1; done`
  - **Verify**: `curl -sf http://localhost:8123/api/ && echo VE1_PASS`
  - **Done when**: HA instance running and responding on :8123
  - **Commit**: None

- [ ] VE2 [VERIFY] E2E check: verify EV Trip Planner integration loads after cleanup
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Read `ui-map.local.md` to find selectors for the EV Trip Planner panel
    2. Navigate to HA on :8123 via browser
    3. Verify EV Trip Planner integration card appears on the overview/dashboard
    4. Verify no JavaScript errors in console related to missing schedule_monitor
    5. Navigate to Settings > Devices & Services > EV Trip Planner entry
    6. Verify integration config page loads without error
    7. Patch `ui-map.local.md` with any newly discovered selectors
  - **Done when**: HA overview loads, integration visible, no console errors for deleted modules, config page loads
  - **Verify**: `echo VE2_PASS`
  - **Commit**: None

- [ ] VE3 [VERIFY] E2E cleanup: stop HA instance and free port
  - **Skills**: e2e, playwright-env, mcp-playwright, playwright-session
  - **Do**:
    1. Kill by PID: `kill $(cat /tmp/ve-pids.txt) 2>/dev/null; sleep 2; kill -9 $(cat /tmp/ve-pids.txt) 2>/dev/null || true`
    2. Kill by port fallback: `lsof -ti :8123 | xargs -r kill 2>/dev/null || true`
    3. Remove PID file: `rm -f /tmp/ve-pids.txt`
    4. Verify port free: `! lsof -ti :8123`
  - **Verify**: `! lsof -ti :8123 && echo VE3_PASS`
  - **Done when**: No process listening on :8123, PID file removed
  - **Commit**: None

## Phase 5: PR Lifecycle

- [ ] 5.1 Push final changes and verify PR is up to date
  - **Do**:
    1. `git push`
    2. Verify PR: `gh pr view --json url,state`
  - **Verify**: `gh pr view --json state | jq -r '.state' | grep -q OPEN && echo PR_LIVE`
  - **Done when**: PR is open with latest changes pushed
  - **Commit**: None

## Notes

- **POC shortcuts**: None -- this is a pure deletion spec with no shortcuts needed
- **AC-1.5 (frontend backups)**: Already done before this spec -- NO-OP
- **AC-1.13 (Lovelace auto-import)**: Confirmed NO-OP -- `async_import_dashboard_for_entry` is active and tested
- **Phase 2 (Refactoring)**: Skipped -- no code to refactor, only deletions
- **Phase 3 (Testing)**: Skipped -- no new tests to write; verification via existing suite
- **Expected LOC reduction**: ~660 source + ~898 test = ~1,558 LOC removed
- **Expected repo size reduction**: ~195 MB (ha-manual directory)
- **Expected test count after**: ~1,815 (1,849 baseline - 34 removed)
