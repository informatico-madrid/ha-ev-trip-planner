---
spec: spec1-dead-code
phase: research
created: 2026-05-09
---

# Research: spec1-dead-code

## Executive Summary

All 13 acceptance criteria verified against current codebase state. AC-1.5 (frontend backup files) is already resolved -- the `.bak`, `.old`, `.fixed` files were removed at some point since the epic research. The remaining 12 ACs are valid and actionable. Vulture analysis reveals additional dead code beyond schedule_monitor (notably `SIGNAL_TRIPS_UPDATED`, `ALL_DAYS` constants, several emhass_adapter methods, and 5+ presence_monitor methods), but these are **out of scope** for this spec (they're called only from tests, or are HA framework callbacks). The `async_import_dashboard_for_entry` deprecation (AC-1.13) is NOT a deprecation -- it's an active, well-tested function. Recommendation: reclassify as NO-OP.

**BMAD Deep-Dive CRITICAL FINDING**: `tests/ha-manual/configuration.yaml` is actively referenced by `scripts/run-e2e.sh:93` and `scripts/run-e2e-soc.sh:85`. Deleting `tests/ha-manual/` (AC-1.12) without first relocating `configuration.yaml` to `scripts/e2e-config/` will **BREAK** `make e2e` and `make e2e-soc`. A pre-step has been added to the implementation order.

## AC Verification Matrix

| AC | Description | Current State | Status | Delta Since Epic |
|----|-------------|---------------|--------|------------------|
| AC-1.1 | `schedule_monitor.py` deleted | File exists (327 LOC) | TODO | Unchanged |
| AC-1.2 | `test_schedule_monitor.py` deleted | File exists (871 LOC, 33 tests) | TODO | Unchanged |
| AC-1.3 | `test_coverage_edge_cases.py` updated | 1 test references schedule_monitor (line 522-548) | TODO | Unchanged |
| AC-1.4 | `*,cover` files added to `.gitignore`, `git rm --cached` | Pattern `*,cover` already in `.gitignore` BUT 19 files still git-tracked | TODO | `.gitignore` already has pattern; needs `git rm --cached` only |
| AC-1.5 | Frontend backup files deleted | **ALREADY DONE** -- only `panel.js` exists in `frontend/` | DONE | Files removed since epic research |
| AC-1.6 | `dashboard.py` remains | Exists (46,495 bytes, ~1,285 LOC) | VERIFIED | Unchanged |
| AC-1.7 | `vehicle_controller.py` remains | Exists (19,650 bytes, ~537 LOC) | VERIFIED | Unchanged |
| AC-1.8 | `make test` passes | 1,849 tests collected | BASELINE | Unchanged |
| AC-1.9 | No new import errors | `ruff check --select F401` passes clean | VERIFIED | Unchanged |
| AC-1.10 | schedule_monitor mutation config removed | Config exists at pyproject.toml line 155-157 | TODO | Unchanged |
| AC-1.11 | `protocols.py,cover` removed | File exists and is git-tracked; `protocols.py` does NOT exist | TODO | Unchanged |
| AC-1.12 | `tests/ha-manual/` deleted | Exists (195 MB, 30 items) | TODO | Unchanged |
| AC-1.13 | Lovelace auto-import gated/removed | `async_import_dashboard_for_entry` is active and tested | TODO | See analysis below |

## Detailed Findings

### AC-1.1 / AC-1.2: schedule_monitor.py and its tests

**Production imports**: ZERO. Confirmed: `grep -rn schedule_monitor custom_components/ --include="*.py"` returns empty.

**Test imports** (3 locations):
1. `tests/test_schedule_monitor.py:12` -- entire file depends on it (33 tests)
2. `tests/test_coverage_edge_cases.py:529` -- 1 test: `test_schedule_monitor_notify_with_none_service`
3. `tests/test_init.py:569` -- `mock_schedule_monitor` method (fixture mock, NOT import of the module)

**Impact**: Deleting schedule_monitor.py + test_schedule_monitor.py removes 34 tests (33 + 1). New test count: ~1,815. AC-1.8 expected "~15-20" drop; actual will be ~34.

**Risk**: LOW. Zero production callers.

### AC-1.3: test_coverage_edge_cases.py update

Single test to remove: `test_schedule_monitor_notify_with_none_service` (lines 522-548). The section header comment at line 522 should also be removed. This is a clean surgical deletion of ~27 lines.

### AC-1.4: .py,cover files

**Git tracking status**: All 19 `*,cover` files are git-tracked despite `.gitignore` having `*,cover` pattern. This means they were added BEFORE the gitignore entry.

**Required action**: `git rm --cached` for each file. No need to add pattern to `.gitignore` (already present).

**Full list of tracked cover files**:
```
custom_components/ev_trip_planner/__init__.py,cover
custom_components/ev_trip_planner/calculations.py,cover
custom_components/ev_trip_planner/config_flow.py,cover
custom_components/ev_trip_planner/const.py,cover
custom_components/ev_trip_planner/coordinator.py,cover
custom_components/ev_trip_planner/dashboard.py,cover
custom_components/ev_trip_planner/definitions.py,cover
custom_components/ev_trip_planner/diagnostics.py,cover
custom_components/ev_trip_planner/emhass_adapter.py,cover
custom_components/ev_trip_planner/panel.py,cover
custom_components/ev_trip_planner/presence_monitor.py,cover
custom_components/ev_trip_planner/protocols.py,cover
custom_components/ev_trip_planner/schedule_monitor.py,cover
custom_components/ev_trip_planner/sensor.py,cover
custom_components/ev_trip_planner/services.py,cover
custom_components/ev_trip_planner/trip_manager.py,cover
custom_components/ev_trip_planner/utils.py,cover
custom_components/ev_trip_planner/vehicle_controller.py,cover
custom_components/ev_trip_planner/yaml_trip_storage.py,cover
```

### AC-1.5: Frontend backup files (RESOLVED)

The three backup files (`panel.js.bak`, `panel.js.old`, `panel.js.fixed`) are **no longer in the working tree**. Only `custom_components/ev_trip_planner/frontend/panel.js` exists. The backups still appear in `mutants/` (mutmut copies) and `tests/ha-manual/` -- both directories are handled by other ACs (AC-1.12 deletes ha-manual, mutants/ is gitignored).

**Action**: Mark as DONE. No work needed.

### AC-1.6 / AC-1.7: dashboard.py and vehicle_controller.py

Both confirmed active. Re-verified:
- `dashboard.py`: 3 direct importers (config_flow.py:52, services.py:19, services.py:1372)
- `vehicle_controller.py`: 14 references across 4 files (trip_manager, emhass_adapter, __init__, README)

No action needed for this spec. Both are god class targets for Spec 3.

### AC-1.10: schedule_monitor mutation config

Located at `pyproject.toml` lines 155-157:
```toml
[tool.quality-gate.mutation.modules.schedule_monitor]
kill_threshold = 0.50
status = "passing"
```

Must be removed when schedule_monitor.py is deleted.

### AC-1.11: protocols.py,cover

`protocols.py` does NOT exist as a source file. The `protocols.py,cover` is an orphaned mutmut artifact. Will be cleaned by the same `git rm --cached` sweep in AC-1.4.

### AC-1.12: tests/ha-manual/

**Size**: 195 MB, 30 items.
**Referenced in**: Makefile (via `--ignore=tests/ha-manual/`), disabled CI workflow (`playwright.yml.disabled:41`).
**Not referenced in**: Any test runner, quality gate, or active workflow.
**Contains**: Full HA test instance with custom_components copy, dashboard YAMLs, configuration files.

**Action**: Delete entire directory. Remove `--ignore=tests/ha-manual/` from Makefile test targets (no longer needed after deletion). Update disabled CI workflow if it references the path.

### AC-1.13: async_import_dashboard_for_entry

**Assessment**: This is NOT deprecated code. It's an active, well-tested function:

- **Defined**: `services.py:1360` -- imports dashboard and calls `import_dashboard()`
- **Called from**: `__init__.py:201` during `async_setup_entry`
- **Tested by**: 7+ tests in `test_init.py` and 3 tests in `test_services_core.py`
- **Purpose**: Auto-imports Lovelace dashboard when a vehicle is configured

**Epic concern**: The epic says "Deprecated Lovelace auto-import gated behind feature flag or removed." However, auto-import is the intended behavior -- users expect their dashboard to appear when they add a vehicle. The "deprecation" label is incorrect.

**Recommendation**: Do NOT gate or remove this function. The auto-import is a core feature. If anything, add a configuration option (in the OptionsFlow) to disable auto-import, but this is Spec 3/4 scope, not Spec 1. For Spec 1, mark AC-1.13 as NO-OP -- the function is not deprecated and should remain unchanged.

## Vulture Dead Code Analysis

Full vulture output (zero confidence threshold) filtered for non-HA-framework items:

### Truly Dead (production code has zero callers, tests have callers only)

| File | Line | Symbol | Production Calls | Test Calls | Verdict |
|------|------|--------|-----------------|------------|---------|
| schedule_monitor.py | 14 | ScheduleMonitor | 0 | 33+ | DEAD -- AC-1.1 |
| utils.py | 34 | ALL_DAYS | 0 | 0 | DEAD -- NEW FINDING |
| const.py | 21 | SIGNAL_TRIPS_UPDATED | 0 | 0 | DEAD -- NEW FINDING |
| const.py | 67 | DEFAULT_CONTROL_TYPE | 0 | 0 | DEAD -- NEW FINDING |
| const.py | 71 | DEFAULT_NOTIFICATION_SERVICE | 0 | 0 | DEAD -- NEW FINDING |

### Test-Only Code (vulture false positive -- called from production via internal paths)

| File | Line | Symbol | Why False Positive |
|------|------|--------|-------------------|
| calculations.py | 102 | get_capacity_kwh | Alias, tested in test_dynamic_soc_capping.py |
| utils.py | 120 | is_valid_trip_id | Used in tests extensively |
| utils.py | 173 | get_trip_time | Used in tests + internal method exists |
| utils.py | 191 | get_day_index | Used in tests + _get_day_index internal |
| sensor.py | 58 | _format_window_time | Tested in test_sensor_coverage.py |
| dashboard.py | 234 | to_dict | Tested in test_dashboard_validation.py |

### HA Framework Callbacks (vulture false positive -- called by HA runtime)

| File | Symbol | HA Callback Type |
|------|--------|-----------------|
| __init__.py | async_setup_entry | HA entry setup |
| __init__.py | async_unload_entry | HA entry unload |
| __init__.py | async_remove_entry | HA entry removal |
| __init__.py | async_migrate_entry | HA migration |
| config_flow.py | async_step_* | HA config flow steps |
| config_flow.py | async_get_options_flow | HA options flow |
| sensor.py | async_setup_entry | HA platform setup |
| coordinator.py | _async_update_data | HA DataUpdateCoordinator |
| diagnostics.py | async_get_config_entry_diagnostics | HA diagnostics |
| sensor.py | *_attr_* | HA Entity attributes |
| sensor.py | extra_state_attributes | HA Entity property |
| sensor.py | device_info | HA Entity property |
| sensor.py | async_will_remove_from_hass | HA Entity lifecycle |

### Dead Methods in Live Modules (scope: Spec 5, not Spec 1)

These methods have zero production callers but are tested. They're candidates for Spec 5 (mutation) or future cleanup, NOT Spec 1:

| Module | Method | Test-Only |
|--------|--------|-----------|
| emhass_adapter | get_assigned_index | Yes |
| emhass_adapter | async_get_integration_status | Yes |
| emhass_adapter | async_handle_emhass_unavailable | Yes |
| emhass_adapter | async_handle_sensor_error | Yes |
| emhass_adapter | async_handle_shell_command_failure | Yes |
| emhass_adapter | get_last_error | Yes |
| emhass_adapter | async_clear_error | Yes |
| emhass_adapter | verify_cleanup | Yes |
| presence_monitor | async_notify_vehicle_not_home | Yes |
| presence_monitor | async_notify_vehicle_not_plugged | Yes |
| presence_monitor | get_home_condition_config | Yes |
| presence_monitor | get_plugged_condition_config | Yes |
| presence_monitor | validate_condition_is_native | Yes |
| panel.py | get_vehicle_panel_url_path | Yes |
| panel.py | get_all_panel_mappings | Yes |
| panel.py | async_register_all_panels | Yes |
| vehicle_controller | set_strategy | Yes |
| vehicle_controller | update_config | Yes |
| vehicle_controller | async_activate_charging | Yes |
| vehicle_controller | reset_retry_state | Yes |
| vehicle_controller | get_retry_state | Yes |
| vehicle_controller | async_deactivate_charging | Yes |
| vehicle_controller | async_get_charging_status | Yes |
| trip_manager | SOCMilestoneResult | Yes |
| trip_manager | _load_trips_yaml | Yes |

**Recommendation**: These are out of scope for Spec 1. Many are error-handling/utility methods that may be called dynamically. Add to Spec 5 backlog for mutation-driven validation.

## New Findings (Not in AC List)

### Finding 1: Dead Constants in const.py

Three constants have zero production AND zero test references:
- `SIGNAL_TRIPS_UPDATED` (line 21)
- `DEFAULT_CONTROL_TYPE` (line 67)
- `DEFAULT_NOTIFICATION_SERVICE` (line 71)

**Recommendation**: Add to Spec 1 scope as AC-1.14. LOW risk, trivial deletion.

### Finding 2: Dead Constant in utils.py

`ALL_DAYS` (line 34) has zero references anywhere.

**Recommendation**: Add to Spec 1 scope as AC-1.14 (combined with above). LOW risk.

### Finding 3: .qwen/settings.json.orig

Found `.qwen/settings.json.orig` (70 bytes) -- orphaned backup file from a settings edit.

**Recommendation**: Delete file. Add AC-1.15 to spec scope.

### Finding 4: mutants/ directory — VERIFIED SAFE

The `mutants/` directory contains old copies of `panel.js.bak`, `panel.js.old`, `panel.js.fixed`, and the entire `tests/ha-manual/` tree.

**Verified**: `mutants/` IS gitignored (line 111 of `.gitignore`). `git check-ignore mutants/` returns "IGNORED". These files are mutmut working copies and do not affect the repo. No action needed.

### Finding 5: Makefile --ignore references to tests/ha-manual/

After deleting `tests/ha-manual/` (AC-1.12), the Makefile still has `--ignore=tests/ha-manual/` flags in test targets. These must be removed to keep the Makefile clean.

**Recommendation**: Add AC-1.16 to remove `--ignore=tests/ha-manual/` from Makefile after directory deletion.

### Finding 6: Dead constants verification — CONFIRMED ZERO REFERENCES

All 4 dead constants verified with grep:

- `SIGNAL_TRIPS_UPDATED` (const.py:21) — only definition + copy in tests/ha-manual/ (being deleted)
- `DEFAULT_CONTROL_TYPE` (const.py:67) — only definition + copy in tests/ha-manual/ (being deleted)
- `DEFAULT_NOTIFICATION_SERVICE` (const.py:71) — only definition + copy in tests/ha-manual/ (being deleted)
- `ALL_DAYS` (utils.py:34) — only definition + copy in tests/ha-manual/ (being deleted)

After tests/ha-manual/ deletion, these constants will have exactly 1 reference each (their own definition). Safe to delete.

### Finding 7: test_init.py mock_schedule_monitor — NOT an import

`tests/test_init.py:569` contains `mock_schedule_monitor` — this is a mock fixture method name, NOT an import of the schedule_monitor module. No action needed when deleting schedule_monitor.py (the mock creates a MagicMock, not importing the real class).

## Risk Assessment

| Deletion | Risk | Impact | Mitigation |
|----------|------|--------|------------|
| schedule_monitor.py | LOW | Removes 327 LOC source | Zero production imports confirmed |
| test_schedule_monitor.py | LOW | Removes 33 tests | All test dead code with schedule_monitor.py |
| test_coverage_edge_cases.py edit | LOW | Removes 1 test | Single test for dead module |
| `git rm --cached` 19 .cover files | LOW | Untracks mutmut artifacts | Already in .gitignore |
| tests/ha-manual/ directory | MEDIUM | 195 MB, disabled CI references | Update Makefile ignores, disabled workflow |
| pyproject.toml schedule_monitor config | LOW | 3 lines removed | Dead module config |
| Dead constants (new finding) | LOW | 4 lines in const.py + utils.py | Grep confirms zero references |

## Test Count Impact

| Action | Tests Removed | Remaining |
|--------|---------------|-----------|
| Current baseline | 0 | 1,849 |
| Delete test_schedule_monitor.py | -33 | 1,816 |
| Remove 1 test from test_coverage_edge_cases.py | -1 | 1,815 |
| **Final** | **-34** | **~1,815** |

Note: AC-1.8 says "test count drops ~15-20". Actual drop is ~34. Update AC expected count.

## Recommendations for Requirements

1. **AC-1.5 is DONE** -- frontend backup files already removed. No action needed.
2. **AC-1.8 test count** -- update expected drop from "~15-20" to "~34" and expected count from "~1,830" to "~1,815".
3. **AC-1.13 Lovelace import** -- function is NOT deprecated. Recommend reclassifying as NO-OP for Spec 1. If gating is desired, defer to Spec 3 (god class refactor of dashboard.py).
4. **New AC-1.14** -- delete dead constants: `SIGNAL_TRIPS_UPDATED`, `DEFAULT_CONTROL_TYPE`, `DEFAULT_NOTIFICATION_SERVICE` (const.py), `ALL_DAYS` (utils.py). Confirmed zero references in production AND tests.
5. **New AC-1.15** -- delete `.qwen/settings.json.orig` (orphaned backup file).
6. **New AC-1.16** -- remove `--ignore=tests/ha-manual/` from Makefile after directory deletion (AC-1.12).
7. **Implementation order**: (a) `git rm --cached` for .cover files, (b) delete schedule_monitor.py + test file + update test_coverage_edge_cases.py, (c) delete tests/ha-manual/, (d) update pyproject.toml mutation config, (e) delete dead constants, (f) delete .qwen/settings.json.orig, (g) clean Makefile ignores, (h) run `make test`, `make e2e`, `make e2e-soc` to verify.

## Open Questions

- Q1: Should dead constants in `const.py` be in Spec 1 or deferred? (Recommend: include, trivial — confirmed zero references)
- Q2: `async_import_dashboard_for_entry` — epic labels it "deprecated" but it's an active feature. Recommend NO-OP for Spec 1. If gating is desired, defer to Spec 3.
- ~~Q3: `mutants/` directory — is it gitignored?~~ **RESOLVED**: Yes, gitignored at line 111 of .gitignore. No action needed.

## Quality Commands

| Type | Command | Source |
|------|---------|--------|
| Lint | `make lint` (ruff + pylint) | Makefile |
| TypeCheck | `make typecheck` (pyright) | Makefile |
| Unit Test | `make test` | Makefile |
| Test + Coverage | `make test-cover` | Makefile |
| Format | `make format` (black + isort) | Makefile |
| Dead Code | `make dead-code` (vulture) | Makefile |
| Unused Deps | `make unused-deps` (deptry) | Makefile |
| Import Check | `make import-check` | Makefile |
| Security Bandit | `make security-bandit` | Makefile |
| Security Audit | `make security-audit` | Makefile |
| Security Gitleaks | `make security-gitleaks` | Makefile |
| Build | N/A (HA custom component, no build step) | -- |

**Local CI**: `make test && make lint && make typecheck`

## Verification Tooling

| Tool | Command | Detected From |
|------|---------|---------------|
| Dev Server | N/A (HA custom component -- loaded by HA) | -- |
| Browser Automation | `@playwright/test ^1.58.2` | devDependencies |
| E2E Config | `playwright.config.ts` | project root |
| Port | 8123 (E2E) / 8124 (staging) | CLAUDE.md |
| Docker | `staging-up/staging-down` Makefile targets | Makefile |

**UI Present**: Yes -- HA panel at `frontend/panel.js`, dashboard YAMLs
**Browser Automation Installed**: Yes (`@playwright/test ^1.58.2`)
**Project Type**: Home Assistant Custom Component (library + frontend panel)
**VE Task Strategy**: Use `make test` for verification. No dev server needed for dead code removal.
**Verification Strategy**: `make test` (confirm no regressions), `make lint` (no new warnings), `git status` (confirm files removed)

## Related Specs

| Spec | Relationship | May Need Update |
|------|-------------|-----------------|
| tooling-foundation (Spec 0) | COMPLETED. Installed vulture, deptry, etc. Used in this research. | No |
| _epics/tech-debt-cleanup | Parent epic. Contains all AC definitions. | Yes -- update AC-1.5 to DONE, AC-1.8 test count |
| spec1-dead-code | This spec | -- |
| solid-refactor-coverage (future Spec 3) | God class targets: dashboard.py, vehicle_controller.py confirmed alive | No |
| m401-emhass-hotfixes | Unrelated milestone | No |
| m403-dynamic-soc-capping | Uses `get_capacity_kwh` alias (vulture finding) -- confirmed alive via test | No |

## BMAD Technical Research Deep-Dive

**Analyst**: Mary (BMAD Business Analyst / Technical Research)
**Date**: 2026-05-09
**Scope**: Complement existing AC-verification research with deep dependency-chain, HA-platform-registration, and cross-artifact analysis.

### 1. Import Graph Analysis: schedule_monitor.py Isolation Proof

**Claim**: schedule_monitor.py has zero production imports.

**Proof via exhaustive search**:

| Search Type | Command | Result |
|-------------|---------|--------|
| Static import | `grep -rn "schedule_monitor" custom_components/ --include="*.py"` | EMPTY -- zero hits |
| Dynamic import (importlib) | `grep -rn "importlib\|__import__\|import_module\|import_string" custom_components/` | EMPTY -- no dynamic import mechanism anywhere in codebase |
| HA platform discovery | `grep -rn "load_platform\|discovery" custom_components/` | EMPTY -- HA platform discovery not used |
| String-based import | No pattern found anywhere in codebase | N/A |
| YAML config reference | `grep -rn "schedule_monitor" custom_components/ --include="*.yaml" --include="*.json"` | EMPTY |
| HA manifest | `manifest.json` contains NO platform list for schedule_monitor | Confirmed |

**Conclusion**: schedule_monitor.py is 100% statically isolated. No dynamic import mechanism exists in the codebase. No HA platform discovery can load it. Safe to delete.

### 2. HA Platform Registration Verification

**PLATFORMS list** (`__init__.py:65`): `[Platform.SENSOR]` -- ONLY sensor. No schedule_monitor.

**manifest.json**: Contains `config_flow: true`, `panel_custom` section, but NO `platforms` key listing schedule_monitor. HA discovers platforms via the PLATFORMS constant in `__init__.py`, not via manifest.

**config_flow.py**: Zero references to schedule_monitor. No setup of ScheduleMonitor class.

**services.yaml**: Zero references to schedule_monitor. No service definitions that would trigger it.

**Conclusion**: schedule_monitor is NOT registered as an HA platform, NOT referenced in config flow setup, NOT discoverable by HA's platform loading mechanism. It was never wired into the integration's setup lifecycle.

### 3. Dead Constants Cross-Artifact Audit

Searched ALL non-Python files (YAML, JSON, TOML, MD, TXT, CFG) for the 4 dead constants:

| Constant | Python References | Non-Python References | Verdict |
|----------|-------------------|----------------------|---------|
| `SIGNAL_TRIPS_UPDATED` | const.py:21 (def only) | ZERO | DEAD |
| `DEFAULT_CONTROL_TYPE` | const.py:67 (def only) | ZERO | DEAD |
| `DEFAULT_NOTIFICATION_SERVICE` | const.py:71 (def only) | ZERO | DEAD |
| `ALL_DAYS` | utils.py:34 (def only) | ZERO | DEAD |

**Files checked**: `services.yaml`, `strings.json`, `config_flow.py`, all `.yaml`/`.json`/`.toml`/`.md`/`.txt`/`.cfg` files in repo root and `custom_components/`. **No references found anywhere.**

**Additional note on `ALL_DAYS`**: It derives from `DAY_ABBREVIATIONS` (line 34: `ALL_DAYS = set(DAY_ABBREVIATIONS.keys())`). `DAY_ABBREVIATIONS` itself IS active (used at lines 89, 271, 274 in utils.py). Only `ALL_DAYS` is dead -- deleting it has zero impact on `DAY_ABBREVIATIONS`.

### 4. tests/ha-manual/ Deep Audit -- CRITICAL FINDING

**BLOCKER**: `tests/ha-manual/configuration.yaml` is actively used by TWO production scripts:

| Script | Line | Usage |
|--------|------|-------|
| `scripts/run-e2e.sh` | 93 | `cp tests/ha-manual/configuration.yaml "${HA_CONFIG_DIR}/configuration.yaml"` |
| `scripts/run-e2e-soc.sh` | 85 | `cp tests/ha-manual/configuration.yaml "${HA_CONFIG_DIR}/configuration.yaml"` |
| `.github/workflows/playwright.yml.disabled` | 41 | `cp tests/ha-manual/configuration.yaml /tmp/ha-e2e-config/configuration.yaml` |

**Impact**: Deleting `tests/ha-manual/` without relocation will **BREAK** `make e2e` and `make e2e-soc`. The disabled CI workflow is also affected but non-blocking (file is `.disabled`).

**Required pre-step**: Before AC-1.12 execution:
1. Create `scripts/e2e-config/configuration.yaml` with the contents of `tests/ha-manual/configuration.yaml` (62 lines, minimal HA config for E2E)
2. Update `scripts/run-e2e.sh:93` to reference `scripts/e2e-config/configuration.yaml`
3. Update `scripts/run-e2e-soc.sh:85` to reference `scripts/e2e-config/configuration.yaml`
4. Update `.github/workflows/playwright.yml.disabled:41` to reference `scripts/e2e-config/configuration.yaml`
5. Only THEN delete `tests/ha-manual/`

**No other ha-manual content is needed**: The E2E scripts only copy `configuration.yaml`. The 63+ dashboard YAML versions, full HA instance, custom_components copies, and all other ha-manual content are unused by active workflows.

**Makefile `--ignore` cleanup**: After ha-manual deletion, remove `--ignore=tests/ha-manual/` from:
- Makefile:6 (`test`)
- Makefile:69 (`test-cover`)
- Makefile:72 (`test-verbose`)
- Makefile:75 (`test-dashboard`)
- Makefile:271 (`test-parallel`)
- Makefile:275 (`test-random`)

### 5. async_import_dashboard_for_entry Deprecation Analysis

**Function chain**:
1. `__init__.py:32` imports `async_import_dashboard_for_entry` from `services.py`
2. `__init__.py:201` calls it during `async_setup_entry` (every vehicle addition)
3. `services.py:1360-1380` defines it: imports `dashboard.import_dashboard` and calls it
4. `config_flow.py:891` also calls `import_dashboard` directly during options flow save

**Test coverage**: 10+ tests in `test_init.py` (class `TestImportDashboard`) + tests in `test_services_core.py`

**Why the epic labels it "deprecated"**: The epic says "Deprecated Lovelace auto-import gated behind feature flag or removed." Analysis shows:
- The function is NOT deprecated -- it's the primary dashboard installation mechanism
- It's called in TWO places: `__init__.py` (first setup) and `config_flow.py` (options save)
- There is NO feature flag mechanism in the codebase (grep for `feature_flag`, `FEATURE_`, `auto_import` returned empty)
- Auto-import is the expected HA pattern: users expect their dashboard to appear when they configure a vehicle

**HA ecosystem context**: Many HA custom components auto-import dashboards (e.g., HACS, Frigate). The pattern of calling `import_dashboard` during `async_setup_entry` is standard. Removing it would make the integration less user-friendly (users would need to manually import YAML).

**Recommendation**: AC-1.13 should be reclassified as NO-OP for Spec 1. The function is not dead, not deprecated, and follows HA conventions. If the epic owner wants a toggle, that belongs in Spec 3 (god class refactor of services.py) or a future spec.

### 6. Mutation Config Cleanup Cross-References

**Single reference**: `pyproject.toml` lines 155-157:

```toml
[tool.quality-gate.mutation.modules.schedule_monitor]
kill_threshold = 0.50
status = "passing"
```

**No other cross-references found**:
- `.claude/skills/` -- zero references to schedule_monitor
- `scripts/` -- zero references to schedule_monitor
- Quality gate scripts -- module-agnostic, read from pyproject.toml at runtime
- `mutmut` config -- uses `paths_to_mutate = ["custom_components/ev_trip_planner"]` (directory-level, not module-level)

**After deletion**: mutmut will scan one fewer file (schedule_monitor.py gone). The `[tool.quality-gate.mutation]` module count drops from 17 to 16. The `global_kill_threshold = 0.48` applies to remaining modules only.

### 7. Dependency Chain Safety Analysis

For each deletion target, traced the full dependency chain:

#### 7a. schedule_monitor.py deletion chain

```
schedule_monitor.py
  ├── imports: const.py (CONF_NOTIFICATION_SERVICE, CONF_VEHICLE_NAME) -- STILL ACTIVE
  ├── imports: homeassistant.core -- framework, unaffected
  ├── imports: homeassistant.helpers.event -- framework, unaffected
  └── imported by: ZERO production files, 3 test files

Downstream deletions required:
  └── tests/test_schedule_monitor.py (33 tests) -- no other file imports from this
  └── tests/test_coverage_edge_cases.py:522-548 (1 test) -- surgical removal
  └── pyproject.toml:155-157 (mutation config) -- 3 lines removed

No transitive breakage. const.py CONF_* constants remain active (used elsewhere).
```

#### 7b. test_schedule_monitor.py deletion chain

```
tests/test_schedule_monitor.py
  ├── imports from: schedule_monitor.py (being deleted)
  ├── imports from: custom_components...const (stays)
  ├── imports from: homeassistant.core (framework)
  ├── NO other test file imports from test_schedule_monitor.py
  └── NO conftest.py fixture references it

Safe to delete. Zero transitive dependencies.
```

#### 7c. Dead constants deletion chain

```
SIGNAL_TRIPS_UPDATED (const.py:21) -- zero importers
DEFAULT_CONTROL_TYPE (const.py:67) -- zero importers
DEFAULT_NOTIFICATION_SERVICE (const.py:71) -- zero importers
ALL_DAYS (utils.py:34) -- zero importers (DAY_ABBREVIATIONS stays)

No transitive breakage. All four are leaf definitions with zero consumers.
```

#### 7d. tests/ha-manual/ deletion chain

```
tests/ha-manual/ (directory)
  ├── USED BY: scripts/run-e2e.sh:93 (configuration.yaml) -- MUST RELOCATE FIRST
  ├── USED BY: scripts/run-e2e-soc.sh:85 (configuration.yaml) -- MUST RELOCATE FIRST
  ├── USED BY: .github/workflows/playwright.yml.disabled:41 -- MUST UPDATE PATH
  ├── referenced by: Makefile --ignore flags (6 targets) -- REMOVE AFTER DELETION
  └── referenced by: docs/specs (historical reference only) -- update if desired

CRITICAL: configuration.yaml MUST be relocated before directory deletion.
```

#### 7e. .py,cover files deletion chain

```
19 tracked .py,cover files
  ├── gitignored already (pattern exists in .gitignore)
  ├── git-tracked (added before gitignore entry)
  └── git rm --cached breaks no imports (these are mutmut artifacts, not importable)

Safe. `git rm --cached` only, no file deletion needed (they'll disappear from tracking).
```

#### 7f. test_init.py mock_schedule_monitor

```
tests/test_init.py:569 mock_schedule_monitor()
  ├── Creates: Mock() + AsyncMock() -- NO import of schedule_monitor module
  ├── Used by: ZERO tests (defined but never called in the file)
  └── Verdict: Orphaned mock fixture. Safe to leave or remove. Not a dependency concern.
```

### 8. Documentation Impact Assessment

Files referencing schedule_monitor that should be updated after deletion:

| File | References | Action |
|------|-----------|--------|
| `docs/architecture.md:171` | Describes schedule_monitor.py module | Remove section |
| `docs/source-tree-analysis.md:24,64` | Lists schedule_monitor.py and its tests | Remove entries |
| `docs/development-guide.md:131` | Lists schedule_monitor.py in tree | Remove entry |
| `docs/MILESTONE_4_POWER_PROFILE.md:279` | References schedule_monitor in planning | Update or leave as historical |
| `docs/MILESTONE_4_1_PLANNING.md:285` | Wire ScheduleMonitor task | Update status to "removed" |
| `docs/DOCS_DEEP_AUDIT.md:99,132` | Lists schedule_monitor in audit | Update entries |

**Recommendation**: Update docs as part of Spec 1 implementation or defer to Spec 7 (lint/format cleanup). Low priority since these are documentation, not code.

### 9. Updated Implementation Order (with ha-manual blocker)

The original implementation order in the research must be revised:

1. **PRE-STEP**: Create `scripts/e2e-config/configuration.yaml` (copy from `tests/ha-manual/configuration.yaml`)
2. **PRE-STEP**: Update `scripts/run-e2e.sh:93`, `scripts/run-e2e-soc.sh:85`, `playwright.yml.disabled:41` to new path
3. (a) `git rm --cached` for 19 .cover files
4. (b) Delete `schedule_monitor.py` + `test_schedule_monitor.py` + update `test_coverage_edge_cases.py`
5. (c) Delete `tests/ha-manual/` (now safe, configuration.yaml relocated)
6. (d) Update `pyproject.toml` mutation config (remove schedule_monitor entry)
7. (e) Delete dead constants from `const.py` and `utils.py`
8. (f) Delete `.qwen/settings.json.orig`
9. (g) Remove `--ignore=tests/ha-manual/` from 6 Makefile targets
10. (h) Update docs (6 files referencing schedule_monitor)
11. (i) Run `make test`, `make e2e`, `make e2e-soc` to verify
12. (j) `make lint && make typecheck` final validation

### 10. Risk Assessment Update

| Risk | Previous Assessment | Updated Assessment | Reason |
|------|--------------------|--------------------|--------|
| tests/ha-manual/ deletion | MEDIUM | **HIGH (blocker)** | Active dependency from E2E scripts -- MUST relocate configuration.yaml first |
| schedule_monitor.py deletion | LOW | LOW (confirmed) | No new findings -- still safe |
| Dead constants deletion | LOW | LOW (confirmed) | No references in any file type |
| Docs staleness | Not assessed | LOW | 6 docs files reference schedule_monitor -- non-blocking |
| mock_schedule_monitor in test_init.py | Not assessed | NEGLIGIBLE | Orphaned fixture, no callers |

## Sources

- `specs/_epics/tech-debt-cleanup/research.md` -- epic validation research
- `specs/_epics/tech-debt-cleanup/research-tools.md` -- tools assessment
- `specs/_epics/tech-debt-cleanup/epic.md` -- AC definitions and scope
- `custom_components/ev_trip_planner/` -- source code verification
- `custom_components/ev_trip_planner/manifest.json` -- HA manifest (no schedule_monitor platform)
- `custom_components/ev_trip_planner/config_flow.py:891` -- direct import_dashboard call (confirms AC-1.13 is NOT deprecated)
- `custom_components/ev_trip_planner/const.py` -- dead constants confirmed zero references
- `custom_components/ev_trip_planner/utils.py` -- ALL_DAYS dead, DAY_ABBREVIATIONS alive
- `scripts/run-e2e.sh:93` -- BLOCKER: references tests/ha-manual/configuration.yaml
- `scripts/run-e2e-soc.sh:85` -- BLOCKER: references tests/ha-manual/configuration.yaml
- `.github/workflows/playwright.yml.disabled:41` -- references tests/ha-manual/configuration.yaml
- `tests/` -- test file analysis
- `.gitignore` -- gitignore pattern verification
- `pyproject.toml:155-157` -- schedule_monitor mutation config (only cross-reference)
- `Makefile` -- 6 test targets with `--ignore=tests/ha-manual/`
- `docs/` -- 6 documentation files referencing schedule_monitor
