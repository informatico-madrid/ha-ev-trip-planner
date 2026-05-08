# Adversarial Review — Tech Debt Cleanup Epic

**Date**: 2026-05-08
**Reviewer**: Architect Mode (Cynical Review) + Deep Investigation
**Content**: `specs/_epics/tech-debt-cleanup/epic.md` + supporting research docs
**Cross-referenced against**: `quality-gate.yaml`, `ROADMAP.md`, `pyproject.toml`, actual file listing, import graph analysis

---

## Findings Summary

| Severity | Count |
|----------|-------|
| CRITICAL — will cause spec execution failure | 5 |
| HIGH — incorrect or missing information | 8 |
| MEDIUM — increases clarity/completeness | 16 |
| LOW — minor improvements | 5 |
| **Total** | **34** |

---

## CRITICAL Findings

### C1: SOLID thresholds contradict quality-gate.yaml

**Epic ARN-001**: "No module exceeds 500 LOC"
**Epic ARN-002**: "No class exceeds 20 public methods"

**quality-gate.yaml** says:
- `srp.max_loc_per_class: 200`
- `srp.max_public_methods: 7`
- `srp.max_arity: 5`

The epic uses relaxed thresholds (500 LOC, 20 methods) while the quality-gate config is MUCH stricter (200 LOC, 7 methods). The epic claims "100% SOLID compliance" but against which standard? If the quality-gate scripts run with their configured thresholds, every spec will FAIL even after the epic's targets are met.

**Fix**: Add a phased threshold approach — Phase 1 meets ARN thresholds (500 LOC, 20 methods), Phase 2 tightens to quality-gate.yaml thresholds (200 LOC, 7 methods). OR update quality-gate.yaml to match ARN thresholds for this epic.

### C2: .venv activation requirement completely absent

ALL Python/bash commands in this project require `. .venv/bin/activate &&` prefix. The epic's Spec 0 installs tools but NEVER mentions:
- That all Python commands must be prefixed with venv activation
- That the .venv must exist before running any tooling
- That CI must also handle venv activation
- That `pip install` commands need the venv active

Without this, every `pip install bandit`, `mutmut run`, `pyright`, etc. will fail or install to the wrong Python.

**Fix**: Add a prerequisite section to Spec 0 and a note in every spec that all commands assume `. .venv/bin/activate` is active.

### C3: dashboard/ directory naming conflict

Spec 3 proposes splitting `dashboard.py` into a `dashboard/` Python package. But `custom_components/ev_trip_planner/dashboard/` ALREADY EXISTS as a directory containing 10+ YAML/JS template files (Lovelace definitions).

Creating a Python package `dashboard/` with `__init__.py` alongside these template files will either:
- Break template loading (if Python treats it as a package)
- Create import confusion
- Require moving templates elsewhere

**Fix**: Either rename the package (e.g., `dashboard_impl/` or `dashboard_manager/`) or move templates to a `templates/` subdirectory within the package. Update all template path references.

### C4: Spec 4 must run AFTER Spec 3 for split modules, not in parallel

Spec 4 modifies function signatures in `calculations.py`, `dashboard.py`, `emhass_adapter.py`. Spec 3 splits these same modules into packages. If Spec 4 runs before or during Spec 3:
- Function locations change (file moves)
- Dataclass imports need updating in new file locations
- Changes may be lost during the split

**Fix**: Spec 4 dependencies should explicitly state: "Must run AFTER Spec 3 for calculations, dashboard, and emhass_adapter modules. Can run in parallel with Spec 3 for other modules."

### C5: mutmut configuration breaks after module splits

When Spec 3 splits `emhass_adapter.py` into `emhass/` package:
- `pyproject.toml [tool.mutmut] paths_to_mutate` still points to flat files
- `[tool.quality-gate.mutation.modules.emhass_adapter]` references a module name that no longer exists
- `mutation_analyzer.py` groups mutants by module name — after splitting, the names change to `emhass.index_manager`, `emhass.load_publisher`, etc.

**Fix**: Add AC to Spec 3 for updating mutmut and quality-gate mutation config after each module split. Add a new AC to Spec 0 for documenting the mutation config update procedure.

---

## HIGH Findings

### H1: schedule_monitor mutation config orphaned after deletion

`pyproject.toml` has `[tool.quality-gate.mutation.modules.schedule_monitor]` with `kill_threshold = 0.50`. After Spec 1 deletes `schedule_monitor.py`, this config entry becomes orphaned. The mutation gate script may fail or produce warnings.

**Fix**: Add AC to Spec 1: "Remove `[tool.quality-gate.mutation.modules.schedule_monitor]` from pyproject.toml after file deletion."

### H2: ruff error count is stale

Epic Section 2 Layer 3 says "Ruff errors: 1 (fixable)". Research confirms `ruff check .` returns "All checks passed!" — zero errors. The epic uses outdated data.

**Fix**: Update to "Ruff errors: 0 (clean)".

### H3: mypy → pyright migration incomplete

Spec 0 says "make typecheck replaces make mypy" but doesn't address:
- `make check` target still depends on `make mypy` — it will break
- The Makefile's `check` target needs updating to call pyright instead
- CI workflow may reference mypy

**Fix**: Add AC: "make check target updated to call pyright instead of mypy. make mypy target removed or converted to a no-op with deprecation message."

### H4: Test count inconsistency between Spec 1 and Spec 2

Spec 1 AC-1.8: "test count drops by ~15-20, new count: ~1,830"
Spec 2 AC-2.8: "make test passes with >= 1,848 tests"

These are contradictory. After Spec 1, the baseline is ~1,830, not 1,848.

**Fix**: Spec 2 AC-2.8 should say ">= 1,830 tests (post-Spec 1 baseline)".

### H5: Missing quality-gate baseline snapshot

The original prompt explicitly requested "un snapshot de quality gate para saber de donde partimos". Spec 0 installs tools but doesn't include running a full baseline snapshot.

**Fix**: Add AC-0.11 to Spec 0: "Run full quality-gate snapshot and save baseline to `_bmad-output/quality-gate/tech-debt-baseline.json`".

### H6: Spec 5 mutation data confuses thresholds with actual scores

The per-module strategy lists "definitions (100% → 80%)" but pyproject.toml shows `kill_threshold = 0.45`. The 100% is the actual kill rate, 0.45 is the minimum threshold. The epic mixes these concepts.

**Fix**: Use research-tools.md actual scores as the "current" column, and pyproject.toml thresholds as the "minimum acceptable" column. Add a third column for "target" (0.80).

### H7: Missing TypeScript tooling in Spec 0

Epic Section 2 defines TypeScript quality targets but Spec 0 doesn't install:
- TypeScript compiler (`tsc`)
- ESLint for TypeScript
- Prettier

Without these, TypeScript quality targets are unmeasurable.

**Fix**: Add ACs to Spec 0 for TypeScript tool installation and configuration.

### H8: Missing deptry and vulture in Spec 0

`quality-gate.yaml` lists `deptry` and `vulture` as recommended tools. `research-tools.md` confirms both are missing. `deptry` is critical for verifying import consistency after module splits (Spec 3). `vulture` detects dead code (directly relevant to Spec 1).

**Fix**: Add deptry and vulture to Spec 0 installation list.

---

## MEDIUM Findings

### M1: Test naming convention ARN incomplete

ARN-008 specifies directory structure but not naming conventions within directories. When 104 files are reorganized, inconsistent naming will result.

**Fix**: Extend ARN-008 with naming convention: `test_{module}_{aspect}.py` for unit tests, `test_{module}_integration.py` for integration tests.

### M2: .cover file handling needs more detail

Spec 1 says "add to .gitignore" but doesn't address:
- Existing tracked files need `git rm --cached`
- `protocols.py,cover` references a non-existent file
- The `.gitignore` pattern must be `*,cover` (comma syntax)

**Fix**: Add AC for `git rm --cached` on existing .cover files and note the protocols.py,cover anomaly.

### M3: tests_excluded_from_mutmut/ not addressed

This directory has 2 test files excluded from mutation testing. Spec 2 doesn't mention what to do with them.

**Fix**: Add AC to Spec 2 for handling excluded test files (keep, move, or integrate).

### M4: Antipattern verification incomplete

Epic claims "0 Tier A antipatterns" but quality-gate.yaml defines 25+ antipattern checks. The checkpoint may not have run all checks.

**Fix**: Add AC to Spec 0 for running full antipattern_checker.py and documenting baseline.

### M5: No rollback strategy

If Spec 3 breaks mid-refactoring, there's no documented rollback plan.

**Fix**: Add section on branching strategy: each spec on its own branch, git tags before each spec, checkpoint commits within specs.

### M6: Interface contracts incomplete for Spec 3

Only TripManager and EMHASSAdapter have interface contracts. services.py, dashboard.py, vehicle_controller.py, and calculations.py also need contracts documented.

**Fix**: Add interface contracts for all 6 modules being split.

### M7: Missing lessons learned section

Original prompt requested "Lecciones aprendidas por cada fase" but the epic has no such section.

**Fix**: Add a "Lessons Learned" template section after each spec.

### M8: ventana_horas production bug not addressed

ROADMAP documents a known bug in `calculations.py:545` where `ventana_horas` is inflated by away time. The epic doesn't capture this.

**Fix**: Add as an AC in Spec 3 or create a pre-cleanup bugfix spec.

### M9: Deprecated Lovelace auto-import not addressed

ROADMAP says `async_import_dashboard_for_entry()` is deprecated but still runs on every setup. This is tech debt directly in scope.

**Fix**: Add AC to Spec 1 or Spec 3 for gating/removing deprecated Lovelace import.

### M10: dashboard.py split insufficient for ARN targets

1,285 LOC split into 2 files = ~642 LOC each, still over ARN-001 (500 LOC). Need at least 3 sub-modules.

**Fix**: Revise dashboard.py split plan to include at least 3 sub-modules.

### M11: E2E-DEBUG log removal may break E2E tests

Spec 7 AC-7.5 removes E2E-DEBUG logs but E2E tests may depend on them. No mitigation plan.

**Fix**: Before removing, verify which E2E tests use these logs. Gate behind environment variable instead of removing.

### M12: Layer 2 weak test threshold alignment

Epic says "< 200 weak tests" but quality-gate.yaml says ANY single-assertion test is an ERROR (zero tolerance). The "< 200" target contradicts the gate config.

**Fix**: Clarify whether legitimate smoke tests get whitelisted or if ALL single-assertion tests must be fixed.

### M13: services.yaml and manifest.json not addressed

When services.py is split into a package, `services.yaml` (HA service definitions) may need updating.

**Fix**: Add AC to Spec 3 for updating HA configuration files after services.py split.

### M14: Playwright CI re-enablement lacks prerequisites

E2E tests assume a running HA instance on localhost:8123. CI doesn't have this.

**Fix**: Either mock HA for CI E2E or document that Playwright CI requires HA test container.

### M15: _bmad-output/ directory management

Quality-gate outputs here but epic doesn't mention .gitignore or baseline storage.

**Fix**: Add AC to Spec 0 for ensuring `_bmad-output/` is in .gitignore and baseline is saved.

### M16: config_flow.py TODO not addressed

`config_flow.py:177` has an active TODO. Spec 7 doesn't address TODOs.

**Fix**: Convert to GitHub issue or document as accepted tech debt.

---

## LOW Findings

### L1: Spec 5 lists schedule_monitor as item 9

Should be removed from the list entirely since it's deleted in Spec 1.

### L2: Epic includes time estimates alongside story points

User instructions forbid time estimates. Remove hour breakdowns, keep story points only.

### L3: ha-manual/ browser cache in tests/

49 directories of browser cache in `tests/ha-manual/`. Should be .gitignored or removed.

### L4: Skills location correction

research-tools.md says `mutation-testing` skill is missing, but it IS available as a global skill at `/home/malka/.roo/skills/mutation-testing/SKILL.md`. The research document needs correction.

### L5: coverage.py config alignment

After module splits and test reorganization, coverage source paths in pyproject.toml need updating. Not mentioned in any spec.

---

## Recommended Priority of Fixes

1. **Apply all CRITICAL fixes first** — these block spec execution
2. **Apply HIGH fixes** — these prevent incorrect measurements
3. **Apply MEDIUM fixes selectively** — focus on M5 (rollback), M6 (contracts), M8 (bug), M10 (split plan)
4. **Apply LOW fixes during implementation** — these are minor

---

## Deep Investigation Findings (Post-Initial Review)

### DI-1: tests/ha-manual/ is NOT browser cache — it is a full HA test instance

**Original claim in research-architecture.md**: "tests/ha-manual/ — HA browser cache - 49 directories of icons, NOT source"

**Actual state**: `tests/ha-manual/` contains a complete Home Assistant test instance:
- `custom_components/ev_trip_planner/` — full copy of the integration
- `ha-manual-config/` — another HA instance with 63+ dashboard YAML versions
- `home-assistant_v2.db` — SQLite database
- Full HA configuration (`configuration.yaml`, `secrets.yaml`, `automations.yaml`)
- `.cache/`, `.cloud/`, `.storage/`, `blueprints/`, `tts/`

This is test infrastructure for E2E/manual testing, NOT browser cache. It should be preserved but the 63+ stale dashboard YAML versions should be cleaned up.

**Fix applied**: AC-1.12 updated to clarify the directory's purpose and scope cleanup to stale YAML versions only.

### DI-2: Import graph verified — all re-exports documented

Complete import graph analysis for Spec 3 module splits:

| Module | Importers | Import Sites |
|--------|-----------|-------------|
| `calculations.py` | `emhass_adapter.py` (4 sites), `trip_manager.py` (7 sites) | 11 total |
| `trip_manager.py` | `__init__.py`, `services.py`, `coordinator.py`, `presence_monitor.py` (TYPE_CHECKING), `vehicle_controller.py` (TYPE_CHECKING) | 5 total |
| `emhass_adapter.py` | `__init__.py`, `coordinator.py`, `trip_manager.py` | 3 total |
| `services.py` | `__init__.py` (10 functions imported) | 1 total (but 10 symbols) |
| `dashboard.py` | `config_flow.py` (2 sites), `services.py` (2 sites) | 4 total |
| `vehicle_controller.py` | `trip_manager.py` | 1 total |

**Key insight**: `calculations.py` has the most import sites (11) and uses both module-level and function-level imports. After splitting into `calculations/` package, all 11 import sites must be verified. The `__init__.py` re-export pattern is critical here.

**Fix applied**: Added detailed interface contracts table to Spec 3 with exact re-export requirements per package.

### DI-3: Quality-gate workflow step mapping

The quality-gate skill uses step-file architecture with 7 steps. Mapping to epic specs:

| QG Step | File | Maps to Epic Spec |
|---------|------|-------------------|
| Step 1 | `step-01-init.md` | Spec 0 (tooling setup) |
| Step 2 | `step-02-layer1.md` | Spec 5 + Spec 6 (test execution, coverage, mutation) |
| Step 3 | `step-03-layer2.md` | Spec 2 + Spec 5 (test quality, weak tests, diversity) |
| Step 3A | `step-03a-layer3a.md` | Spec 7 (Tier A smoke test: ruff, pyright, SOLID) |
| Step 4 | `step-04-layer3b.md` | Spec 3 (Tier B BMAD Party Mode: SOLID Tier B, antipatterns) |
| Step 5 | `step-05-checkpoint.md` | All specs (checkpoint JSON generation) |
| Step 6 | `step-06-layer4.md` | Spec 8 (security and defense) |

**Quality-gate execution order**: L3A → L1 → L2 → L3B → L4 (fail-fast design).

**Fix applied**: Added workflow mapping to Notes section.

### DI-4: dashboard/ directory contents verified

11 files in `custom_components/ev_trip_planner/dashboard/`:
- `dashboard.yaml`, `dashboard-create.yaml`, `dashboard-edit.yaml`, `dashboard-delete.yaml`, `dashboard-list.yaml`
- `ev-trip-planner-full.yaml`, `ev-trip-planner-simple.yaml`, `ev-trip-planner-{vehicle_id}.yaml`
- `dashboard.js`, `ev-trip-planner-simple.js`
- `dashboard_chispitas_test.yaml` (test configuration)

When `dashboard.py` becomes a package `dashboard/`, these files must move to `dashboard/templates/` to avoid conflicts with `__init__.py`. The `dashboard_chispitas_test.yaml` suggests test-specific templates that may be referenced in tests.

**Status**: Already addressed in epic AC-3.0 with `dashboard/templates/` subdirectory.

### DI-5: research-architecture.md error on vehicle_controller.py

The research-architecture.md Section 3.2 says "vehicle_controller.py — ACTIVE (NOT dead)" but the table in Section 1.1 says "vehicle_controller.py | 537 | 8 | 40 | DEAD CODE (see Section 3.2)". The table label is WRONG — it says DEAD CODE but the section says ACTIVE. This inconsistency in the research document could cause confusion.

**Status**: Research document inconsistency noted. The epic correctly identifies vehicle_controller.py as active.
