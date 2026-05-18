# Validation Research: Tech Debt Cleanup Epic

## Validation Findings

### 1. schedule_monitor.py — DEAD CODE (PARTIALLY CORRECT)

**Claim in epic**: "confirmed 0 imports from any active code path"

**Verification**:
- **Source imports**: Zero. No Python file in `custom_components/ev_trip_planner/` imports `schedule_monitor`. Only `README.md` mentions it by name.
- **Test imports**: TWO test files import it:
  - `tests/test_schedule_monitor.py` (line 12): `from custom_components.ev_trip_planner.schedule_monitor import ScheduleMonitor, VehicleScheduleMonitor`
  - `tests/test_coverage_edge_cases.py` (line 529): imports from `schedule_monitor` for edge case testing

**Verdict**: schedule_monitor.py IS dead code in production (zero active code path imports). Deleting it WILL break two test files that need to be deleted as part of the same spec. **Spec 1 acceptance criteria need updating** to include deletion of these two test files.

**Risk**: MEDIUM — deleting the module without removing the two test imports will cause `make test` to fail (tests will have import errors). The epic correctly identifies this as dead code but doesn't explicitly call out that the test files need deletion too.

### 2. dashboard.py — NOT DEAD CODE (EPIC PARTIALLY WRONG)

**Claim in epic**: "dashboard.py remains (it IS imported), but verify all 11 dashboard YAML/JS templates are active"

**Verification**:
- `config_flow.py` (line 52): `from .dashboard import import_dashboard, is_lovelace_available`
- `config_flow.py` (line 891): calls `await import_dashboard(...)` — active production use
- `services.py` (line 19): `from .dashboard import DashboardImportResult`
- `services.py` (line 1372): `from .dashboard import import_dashboard as import_dashboard` — active production use
- `__init__.py` (line 32): imports `async_import_dashboard_for_entry` from services.py (transitive dependency)
- `__init__.py` (line 201): calls `await async_import_dashboard_for_entry(hass, entry, vehicle_id)` — active production use

**Verdict**: dashboard.py IS actively used. 3 direct importers (config_flow, services, init via services). The epic's assessment is correct. However, `dashboard.py` is 1,285 LOC — it should be listed in Spec 3 as one of the god classes needing splitting (ARN-001 violation at 1,285 LOC, well over 500 line limit). **The epic mentions `dashboard.py` in ARN-003 for high-arity but does NOT list it as a target for Spec 3 god-class splitting.** This is a gap.

### 3. Circular Import Cycles — VERIFIED (3 cycles confirmed)

**Import chain verification**:

| Chain | Direction | Status |
|-------|-----------|--------|
| `coordinator` -> `trip_manager` -> `sensor` -> `coordinator` | Direct imports | Confirmed cycle |
| `trip_manager` -> `vehicle_controller` -> `presence_monitor` -> `trip_manager` | Direct imports | Confirmed cycle |
| `trip_manager` -> `vehicle_controller` -> `trip_manager` | Direct import in vehicle_controller.py line 14 | Confirmed cycle |

**`from __future__ import annotations` status**:
- `coordinator.py`: NOT used (no `from __future__` header)
- `sensor.py`: HAS it (line 7)
- `trip_manager.py`: HAS it (line 8)
- `vehicle_controller.py`: NOT used
- `presence_monitor.py`: NOT used

**Verdict**: Only 2 of 5 modules in the cycles use `from __future__ import annotations`. The `from __future__ import annotations` in `sensor.py` and `trip_manager.py` prevents some but not all cycles. The cycles still exist at runtime because some imports happen inside functions (local imports in trip_manager.py at lines 732, 794, 893, 931). The epic's claim of "3 cycles" is correct. Fixing them requires adding `from __future__ import annotations` to `coordinator.py`, `vehicle_controller.py`, and `presence_monitor.py` PLUS fixing the remaining local imports.

### 4. vehicle_controller.py — WIRING VERIFIED

**Usage count**: 14 references across 4 files (non-test):
- `trip_manager.py` (lines 42, 120, 391, 2291-2295): Full instantiation and usage
- `emhass_adapter.py` (lines 1020-1021, 1530-1531): Access via `trip_manager.vehicle_controller`
- `__init__.py` (lines 147-150): Access via `trip_manager.vehicle_controller._presence_monitor`
- `README.md`: Documentation reference

**Verdict**: vehicle_controller.py IS wired in. Correctly classified as "remains" in Spec 1. However, its 537 LOC violates ARN-001 (500 LOC limit). Should be included in Spec 3 as a module needing split.

### 5. Test Count Verification

| Metric | Epic Claim | Actual | Status |
|--------|-----------|--------|--------|
| pytest collected tests | 1,848 | 1,849 | Matches (+1) |
| Total test files | ~107 | 104 Python + 10 TypeScript = 114 | Epic says "~107 test files (~1,848 tests)" — undercount by ~7 files |
| Python test files | — | 104 | — |
| TypeScript spec files | — | 10 (9 in e2e/ + 1 in e2e-dynamic-soc/) | TypeScript tests exist but not counted in epic |
| Flat test files (top-level) | 104 | 104 | All in flat structure |

**test_trip_manager\*.py files**: 13 actual files (not 13 "concerns")
**test_config_flow\*.py files**: 6 actual files (matches epic)

### 6. assert True — VERIFIED (2 found, NOT 2 in tests)

**Locations**:
- `tests/test_init.py:830`: `assert True, "Placeholder implementation - cleanup not yet active"`
- `tests/test_missing_coverage.py:551`: bare `assert True`

Epic correctly claims 2 `assert True` violations. Both are in test code.

### 7. Dead Code Removal Safety — SPEC 1 NEEDS UPDATE

**Critical finding**: Deleting schedule_monitor.py requires deleting two dependent test files:
- `tests/test_schedule_monitor.py` (87 lines)
- `tests/test_coverage_edge_cases.py` contains imports from schedule_monitor at line 529

**dashboard.py,cover** exists (mutmut-generated coverage file). This is NOT a backup file — it's a coverage data file with comma-separated naming. The epic calls them "backup files" but they're artifact files from coverage tools.

**Total .py,cover files**: 19 in source dir + ~14 in mutants/ dir (mutmut generated). The epic says "18 files" — close but not exact. These should be added to `.gitignore` not moved to `_docs/`.

### 8. Missing Pieces in Epic

**panel.py — God class NOT captured in Spec 3**:
- `panel.py` is 248 LOC (under 500 line limit), so technically compliant with ARN-001. But it's a Home Assistant frontend panel in Python. The epic does not address it for Spec 3 god-class splitting, which is correct since it's not a god class.

**panel.js — Backup files EXISTS**:
- `frontend/panel.js` (66,502 bytes — active)
- `frontend/panel.js.bak` (24,200 bytes — backup)
- `frontend/panel.js.old` (24,200 bytes — backup)
- `frontend/panel.js.fixed` (79,900 bytes — backup/alternate)
- `frontend/panel.css` (18,628 bytes — CSS, not a backup)
- `frontend/lit-bundle.js` (23,887 bytes — compiled bundle)

Epic correctly claims 3 backup files in Spec 1 AC-1.3. The `.fixed` file is larger than active, suggesting it may be a work-in-progress version.

**dashboard.py NOT listed as god class target for Spec 3**:
- 1,285 LOC, violates ARN-001 (500 line limit)
- Should be split in Spec 3 but epic only lists emhass_adapter, trip_manager, and services

**vehicle_controller.py NOT listed as god class target for Spec 3**:
- 537 LOC, violates ARN-001 (500 line limit)
- Should be split in Spec 3 but epic only lists emhass_adapter, trip_manager, and services

**calculations.py NOT listed as god class target for Spec 3**:
- 1,690 LOC, violates ARN-001 (500 line limit)
- Only addressed in Spec 4 for arity but not in Spec 3 for splitting

**protocols.py DOES NOT EXIST**:
- `protocols.py,cover` exists (coverage artifact) but `protocols.py` does not. This may be a deleted file or a planned module. Not relevant to epic.

### 9. Dependency Graph Issues

| Spec | Claimed Dependencies | Issues |
|------|---------------------|--------|
| Spec 1 -> Spec 0 | Spec 0 first | **Disagree**. Spec 1 (dead code removal) has zero dependencies on tools. Can run in parallel or before Spec 0. |
| Spec 2 -> Spec 1 | Dead code out first | **Disagree**. Test reorganization is independent of dead code removal. Both can run in parallel. |
| Spec 3 -> Spec 2 | Test reorganization first | **Agree**. Refactoring without organized tests is risky. |
| Spec 4 -> Spec 3 | God classes first | **Disagree**. Arity fixes are mechanical and independent of module splits. Can run in parallel with Spec 3. |
| Spec 5 -> Spec 3, Spec 4 | Refactoring first | **Partially agree**. After refactoring, tests are easier but mutation work on existing code is also valuable. Spec 5 can start before Spec 3 completes. |
| Spec 8 -> Spec 0, Spec 7 | Tools + cleanup first | **Agree**. |

**Recommended dependency corrections**:
- Spec 1: NO dependencies (runs independently, parallel with Spec 0)
- Spec 2: NO dependencies (runs independently, parallel with Spec 1)
- Spec 3: Depends on Spec 2 (test safety net)
- Spec 4: NO dependencies (independent mechanical change)
- Spec 5: Can start in parallel with Spec 2 (no hard dependency on refactoring)
- Spec 6: Can start in parallel with Spec 5

### 10. Scope/Size Realism Assessment

| Spec | Epic Estimate | Assessment | Rationale |
|------|--------------|------------|-----------|
| Spec 0: Tooling | 0.5 SP (5h) | REASONABLE | Simple installs and Makefile additions |
| Spec 1: Dead Code | 0.25 SP (2h) | REASONABLE | Just deletions, but needs to include test file cleanup |
| Spec 2: Test Reorg | 1.0 SP (8-12h) | UNDERESTIMATED | 104 flat files reorganized into 3+ directories is complex. Test consolidation alone (13 trip_manager files -> 3) needs careful dedup analysis. Recommend 1.5-2.0 SP. |
| Spec 3: God Classes | 3.0 SP (24-36h) | SEVERELY UNDERESTIMATED | Splitting 3 modules (emhass_adapter 2,730 LOC, trip_manager 2,503 LOC, services 1,635 LOC) PLUS dashboard (1,285 LOC) PLUS vehicle_controller (537 LOC) PLUS calculations (1,690 LOC) = 11,373 LOC to reorganize. Each split requires: module creation, import migration, test migration, API preservation. 15-25 hours per module minimum. Recommend 8-12 SP. |
| Spec 4: Arity | 0.5 SP (8-12h) | REASONABLE | Mechanical dataclass conversions |
| Spec 5: Mutation | 4.0 SP (40-60h) | UNDERESTIMATED | 49% -> 100% kill rate is aggressive. 17 modules need significant test improvements. Recommend 6-8 SP. |
| Spec 6: Coverage | 1.0 SP (12-16h) | UNDERESTIMATED | 273 pragma locations across 9 files. Many are in complex IO paths. Recommend 2-3 SP. |
| Spec 7: Lint/Type | 0.25 SP (4-6h) | REASONABLE | Mostly automated fixes + 16 sensor.py pyright errors |
| Spec 8: Security | 0.5 SP (4-6h) | REASONABLE | Tool installs + CI updates |

### 11. pyright Errors in sensor.py — VERIFIED

Exactly 16 errors, all `reportIncompatibleVariableOverride` or `reportIncompatibleVariableOverride`:
- Lines 81, 158, 377, 933: `available` definition incompatible
- Lines 129, 197, 434, 965: `native_value` override incompatible
- Lines 137, 204, 445, 984: `extra_state_attributes` override incompatible
- Lines 147, 347, 462, 1027: `device_info` override incompatible

These are all Home Assistant API compatibility issues (HA Entity properties changed type in newer HA versions). Epic correctly targets these in Spec 7.

### 12. ruff Status — VERIFIED

`ruff check` passes with zero errors. Epic claims "1 (fixable)" — this may have been fixed recently. Current state is clean.

### 13. TypeScript Files — NOT CAPTURED IN EPIC

Epic focuses on Python debt but ignores:
- 10 TypeScript files (9 in `tests/e2e/`, 1 in `tests/e2e-dynamic-soc/`)
- `tsconfig.e2e.json` at project root
- `playwright.config.ts`, `playwright.soc.config.ts`
- `globalTeardown.ts`, `auth.setup.ts`, `auth.setup.soc.ts`

The epic claims "zero warnings" and "all linters passing" as targets. TypeScript linting is not addressed.

### 14. Missing Specs

| Missing Spec | Rationale |
|-------------|-----------|
| Dashboard module split | dashboard.py (1,285 LOC) is a god class target not captured in Spec 3 |
| vehicle_controller split | 537 LOC, violates ARN-001 |
| calculations.py split | 1,690 LOC, violates ARN-001 |
| TypeScript lint | ts files exist but epic has zero TypeScript quality gates |
| .cover file cleanup | 19 `*.py,cover` files exist as mutmut artifacts; epic calls them "backup files" but they're coverage data artifacts that should be `.gitignore`d, not moved |

## Summary Table

| Epic Claim | Actual State | Verdict |
|-----------|-------------|---------|
| schedule_monitor.py dead | Dead in production, 2 test files depend on it | PARTIALLY CORRECT — needs test cleanup |
| dashboard.py imported | Yes, 3 direct importers in production code | CORRECT |
| 3 circular import cycles | 3 confirmed (coordinator, vehicle_controller, presence_monitor) | CORRECT |
| vehicle_controller wired | 14 references across 4 files | CORRECT |
| ~107 test files | 104 Python + 10 TypeScript = 114 | CLOSE (off by 7-10) |
| 1,848 tests | 1,849 collected | CORRECT |
| 2 `assert True` | 2 found in test_init.py and test_missing_coverage.py | CORRECT |
| 18 `.cover` backup files | 19 `*.py,cover` mutmut artifacts (not backups) | CLOSE (artifact type mismatch) |
| panel.js backups | 3 found: .bak, .old, .fixed | CORRECT |
| 0 pyright errors | 16 errors in sensor.py | CORRECT (pre-existing) |
| 1 ruff error | 0 ruff errors (already fixed) | STALE |
| God classes: emhass_adapter, trip_manager, services | Also dashboard (1,285 LOC), vehicle_controller (537 LOC), calculations (1,690 LOC) | INCOMPLETE |
| Spec 1 depends on Spec 0 | No actual dependency | INCORRECT |
| Spec 2 depends on Spec 1 | No actual dependency | INCORRECT |
| Spec 4 depends on Spec 3 | No hard dependency | INCORRECT |
| Total: ~11 SP | More like ~18-25 SP | UNDERESTIMATED |
