# Architecture Research — Technical Debt Triage

Date: 2026-05-08
Epic: tech-debt-cleanup

---

## 1. Project Landscape Overview

### 1.1 Source Code Statistics

**18 Python modules, 15,097 total lines of source code.**

| Module | LOC | Classes | Methods | SOLID Issues |
|--------|-----|---------|---------|-------------|
| `emhass_adapter.py` | 2,730 | 1 | 41 | GOD CLASS (2730 LOC, 41 methods) |
| `trip_manager.py` | 2,503 | 3 | 49 | GOD CLASS (2503 LOC, 49 methods), HIGH ARITY |
| `services.py` | 1,635 | 0 | 27 | SRP violation (handles 12+ responsibilities) |
| `calculations.py` | 1,690 | 2 | 21 | SRP violation (monolithic calc engine) |
| `dashboard.py` | 1,285 | 5 | 20 | POTENTIAL DEAD CODE (see Section 3.1) |
| `config_flow.py` | 1,038 | 2 | 15 | Moderate (1038 LOC) |
| `sensor.py` | 1,041 | 4 | 28 | 16 pyright type errors (see Section 5.1) |
| `presence_monitor.py` | 806 | 1 | 20 | Moderate (806 LOC, 20 methods) |
| `vehicle_controller.py` | 537 | 8 | 40 | DEAD CODE (see Section 3.2) |
| `schedule_monitor.py` | 327 | 2 | 15 | DEAD CODE (see Section 3.3) |
| `coordinator.py` | 320 | 1 | 5 | Clean |
| `utils.py` | 356 | 0 | 10 | Clean |
| `panel.py` | 248 | 0 | 7 | Clean |
| `__init__.py` | 227 | 1 | 6 | Clean |
| `const.py` | 110 | 0 | 0 | Clean |
| `definitions.py` | 97 | 1 | 1 | Clean |
| `diagnostics.py` | 82 | 0 | 1 | Clean |
| `yaml_trip_storage.py` | 65 | 1 | 3 | Clean |

### 1.2 High-arity Functions (8+ parameters)

All identified in `calculations.py` — these are pure functions but have parameter lists that violate readability:

| Line | Function | Params |
|------|----------|--------|
| 610 | `calculate_multi_trip_charging_windows` | 9 |
| 870 | `calculate_deficit_propagation` | 9 |
| 1148 | `calculate_power_profile_from_trips` | 8 |
| 1357 | `calculate_power_profile` | 8 |

Also:
- `dashboard.py:205` `DashboardImportResult.__init__` — 8 params
- `emhass_adapter.py:586` `EMHASSAdapter._populate_per_trip_cache_entry` — 12 params (TIGHTEST VIOLATION)

---

## 2. SOLID Violations

### 2.1 SRP — Single Responsibility Principle (Tier A)

**`EMHASSAdapter`** (`emhass_adapter.py`, 2730 LOC, 41 methods) — Most severe violation:
- Index management (assign/release/cleanup)
- Deferrable load publishing
- Error handling and notifications
- Caching and state management
- Power profile calculation
- Schedule generation
- Config entry listening

**`TripManager`** (`trip_manager.py`, 2503 LOC, 49 methods):
- CRUD operations (add/update/delete/list trips)
- Emhass synchronization logic
- SOC calculations (calcular_ventana_carga, calcular_hitos_soc, etc.)
- Power profile generation
- Deferrables schedule generation
- Vehicle controller management
- Sensor update logic

**`services.py`** (0 classes, 27 functions):
- Service handlers (12 different service handlers)
- Dashboard import helpers (2 functions)
- Panel registration (2 functions)
- Cleanup operations (4 functions)
- Configuration builders (1 function)
- Static path registration (1 function)

### 2.2 OCP — Open/Closed Principle

- No polymorphism in critical paths. Strategy pattern exists in `vehicle_controller.py` but only 2 of 5 strategies have implementations.
- `dashboard.py` has conditional logic for different storage backends that could be abstracted.

### 2.3 LSP — Liskov Substitution Principle

- `vehicle_controller.py` has 5 strategy classes (`SwitchStrategy`, `ServiceStrategy`, `ScriptStrategy`, `ExternalStrategy`, `VehicleControlStrategy` base). All implement the same interface, so LSP is technically upheld, but the strategy pattern is underutilized (only 2 strategies are actively instantiated).

### 2.4 ISP — Interface Segregation Principle

- `VehicleControlStrategy` ABC has `activate`, `deactivate`, `get_status` — `ExternalStrategy` implements stubs for all three, suggesting the interface could be split.

### 2.5 DIP — Dependency Inversion Principle

- No DI container. Dependencies are directly instantiated within modules.
- `trip_manager.py` directly instantiates `VehicleController`.
- `emhass_adapter.py` directly references `trip_manager.vehicle_controller` (conditional coupling).

---

## 3. Dead / Potentially Dead Code

### 3.1 dashboard.py — POTENTIALLY ACTIVE (Tier A)

**File:** `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/dashboard.py`
**Size:** 1,285 LOC, 5 classes, 20 methods

**NOT dead code.** It IS imported and used:
- `config_flow.py:52` imports `import_dashboard, is_lovelace_available`
- `config_flow.py:881` uses `is_lovelace_available()`
- `config_flow.py:891` calls `await import_dashboard()`
- `services.py:1360` defines `async_import_dashboard_for_entry()` which calls `import_dashboard()`
- `__init__.py:32,200-201` imports and calls dashboard helpers

**However:** The `dashboard/` subdirectory contains 11 YAML/JS files that are dashboard templates (Lovelace definitions), not actively maintained code:
- `dashboard.yaml`, `ev-trip-planner-full.yaml`, `ev-trip-planner-simple.yaml` (templates)
- `dashboard.js`, `ev-trip-planner-simple.js` (JS handlers)
- Multiple dated backup files: `panel.js.bak`, `panel.js.old`, `panel.js.fixed`

### 3.2 vehicle_controller.py — ACTIVE (NOT dead)

**File:** `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/vehicle_controller.py`
**Size:** 537 LOC, 8 classes, 40 methods

**Wired into trip_manager.py:**
- `trip_manager.py:42` imports `VehicleController`
- `trip_manager.py:120` instantiates it: `self.vehicle_controller = VehicleController(...)`
- `trip_manager.py:391` calls `await self.vehicle_controller.async_setup()`
- Multiple other references throughout `trip_manager.py`

**Strategy pattern underutilized:** 5 strategy classes exist but only a subset are actually instantiated with config-driven selection.

### 3.3 schedule_monitor.py — CONFIRMED DEAD CODE (Tier A)

**File:** `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/schedule_monitor.py`
**Size:** 327 LOC, 2 classes, 15 methods

**NOT imported from anywhere.** Zero references in any other file:
- `grep -rn 'schedule_monitor' custom_components/ --include='*.py'` returns NO results (other than the file itself)
- Has a `TODO` comment at line 190: "TODO: Implement proper schedule parsing"

**This is dead code. Safe to delete.**

### 3.4 Backup/Obsolete Files

The following files appear to be abandoned backups or cover reports:

| File | Size | Notes |
|------|------|-------|
| `calculations.py,cover` | 44,001 bytes | Coverage report (not code) |
| `config_flow.py,cover` | 41,976 bytes | Coverage report |
| `const.py,cover` | 3,287 bytes | Coverage report |
| `dashboard.py,cover` | 46,404 bytes | Coverage report |
| `emhass_adapter.py,cover` | 68,361 bytes | Coverage report |
| `panel.py,cover` | 7,940 bytes | Coverage report |
| `presence_monitor.py,cover` | 29,249 bytes | Coverage report |
| `schedule_monitor.py,cover` | 12,467 bytes | Coverage report |
| `sensor.py,cover` | 35,655 bytes | Coverage report |
| `services.py,cover` | 60,031 bytes | Coverage report |
| `trip_manager.py,cover` | 85,281 bytes | Coverage report |
| `utils.py,cover` | 11,139 bytes | Coverage report |
| `vehicle_controller.py,cover` | 20,374 bytes | Coverage report |
| `yaml_trip_storage.py,cover` | 2,415 bytes | Coverage report |
| `frontend/panel.js.bak` | 24,200 bytes | Backup JS file |
| `frontend/panel.js.old` | 24,200 bytes | Backup JS file |
| `frontend/panel.js.fixed` | 79,900 bytes | "Fixed" JS version (unused) |

**Recommendation:** Move all `*.cover` files to a `_docs/` directory or exclude from version control. The `panel.js.bak`, `panel.js.old`, `panel.js.fixed` in `frontend/` are obsolete backups.

---

## 4. Circular Import Dependencies

**3 circular dependency cycles detected:**

```
Cycle 1: coordinator -> trip_manager -> sensor -> coordinator
Cycle 2: trip_manager -> vehicle_controller -> presence_monitor -> trip_manager
Cycle 3: trip_manager -> vehicle_controller -> trip_manager
```

### 4.1 Cycle 1 — coordinator -> trip_manager -> sensor -> coordinator

- `coordinator.py:30` imports `from .trip_manager import TripManager`
- `trip_manager.py:40` imports `from .sensor import async_update_trip_sensor`
- `sensor.py:22` imports `from .coordinator import TripPlannerCoordinator`

**Risk:** Moderate. These imports are at module level and could cause initialization order issues.

### 4.2 Cycle 2 — trip_manager -> vehicle_controller -> presence_monitor -> trip_manager

- `trip_manager.py:42` imports `from .vehicle_controller import VehicleController`
- `vehicle_controller.py:21` imports `from .presence_monitor import PresenceMonitor`
- `presence_monitor.py:16` imports `from .trip_manager import TripManager` (used in type hints)

**Risk:** High. `PresenceMonitor` imports `TripManager` only for type hints (`TYPE_CHECKING`). Should use `from __future__ import annotations` or move the import inside the function.

### 4.3 Cycle 3 — trip_manager -> vehicle_controller -> trip_manager

- `trip_manager.py:42` imports `from .vehicle_controller import VehicleController`
- `vehicle_controller.py:22` imports `from .trip_manager import TripManager` (used for type hints in signatures)

**Risk:** Moderate. Both use each other for type annotations. Could be resolved with string type annotations.

### 4.4 Complete Import Graph (Internal Only)

```
calculations -> utils, const
config_flow -> dashboard, const
coordinator -> emhass_adapter, const, trip_manager
emhass_adapter -> const, calculations
__init__ -> trip_manager, panel, emhass_adapter, yaml_trip_storage, utils, coordinator, services, const
panel -> const
presence_monitor -> const, trip_manager
schedule_monitor -> const  (DEAD CODE)
sensor -> definitions, coordinator, const
services -> sensor, trip_manager, panel, utils, coordinator, dashboard, const
trip_manager -> sensor, emhass_adapter, yaml_trip_storage, const, utils, calculations, vehicle_controller
vehicle_controller -> presence_monitor, const, trip_manager
yaml_trip_storage -> const
```

---

## 5. Test Architecture

### 5.1 Test File Organization

**No unit/integration directory separation.** All 104 Python test files are flat in `tests/`:
```
tests/
  conftest.py           (22,042 bytes)
  __init__.py
  setup_entry.py
  e2e/                  (10 Playwright .spec.ts files)
  e2e-dynamic-soc/      (2 Playwright .spec.ts files + helpers)
  fixtures/             (YAML dashboards, trip/vehicle JSON fixtures)
  ha-manual/            (HA browser cache - 49 directories of icons, NOT source)
  logs/
  test_*.py             (104 files, all flat)
```

**No separation between:**
- Unit tests (mocked dependencies)
- Integration tests (real HA instance)
- E2E tests (browser-based)

### 5.2 Test Module Coverage

| Source Module | Test Files | Coverage Ratio |
|---------------|-----------|----------------|
| `trip_manager.py` (2503 LOC, 49 methods) | 13 | Heavy focus |
| `config_flow.py` (1038 LOC, 15 methods) | 6 | Moderate |
| `dashboard.py` (1285 LOC, 20 methods) | 5 | Moderate |
| `sensor.py` (1041 LOC, 28 methods) | 4 | Moderate |
| `emhass_adapter.py` (2730 LOC, 41 methods) | 3 | Low for size |
| `coordinator.py` (320 LOC, 5 methods) | 2 | Good |
| `vehicle_controller.py` (537 LOC, 40 methods) | 2 | Low for method count |
| `presence_monitor.py` (806 LOC, 20 methods) | 2 | Moderate |
| `calculations.py` (1690 LOC, 21 methods) | 1 | **Very low** |
| `services.py` (1635 LOC, 27 methods) | 1 | **Very low** |
| `utils.py` (356 LOC, 10 methods) | 1 | Moderate |
| `panel.py` (248 LOC, 7 methods) | 3 | Good |
| `yaml_trip_storage.py` (65 LOC, 3 methods) | 1 | Good |
| `schedule_monitor.py` (327 LOC, 15 methods) | 1 | Low (but dead code) |

### 5.3 Orphaned / Bug-Finding Test Files

Many test files appear to be one-off bug regression tests rather than proper test suites. Examples:
- `test_aggregated_sensor_bug.py` (122,338 bytes — abnormally large for a test)
- `test_charging_window_bug_fix.py`
- `test_def_end_bug_red.py`
- `test_def_start_window_bug.py`
- `test_emhass_arrays_ordering_bug.py`
- `test_recurring_day_offset_bug.py`
- `test_soc_100_propagation_bug.py`
- `test_timezone_utc_vs_local_bug.py`
- `test_t32_and_p11_tdd.py`
- `test_t34_integration_tdd.py`
- `test_three_trips_charging_positions.py`

These are scattered across the flat test directory with no logical grouping.

### 5.4 Coverage Test Files

Multiple test files are explicitly coverage-driven:
- `test_coverage_100_percent.py`
- `test_coverage_edge_cases.py`
- `test_coverage_remaining.py`
- `test_dashboard_coverage_missing.py`
- `test_emhass_adapter_trip_id_coverage.py`
- `test_missing_coverage.py`
- `test_sensor_coverage.py`
- `test_trip_manager_missing_coverage.py`

This suggests a "fill coverage gaps" testing strategy rather than behavior-driven testing.

### 5.5 E2E Tests

**10 Playwright E2E spec files** in `tests/e2e/` and `tests/e2e-dynamic-soc/`:
- `create-trip.spec.ts`
- `delete-trip.spec.ts`
- `edit-trip.spec.ts`
- `form-validation.spec.ts`
- `trip-list-view.spec.ts`
- `emhass-sensor-updates.spec.ts`
- `panel-emhass-sensor-entity-id.spec.ts`
- `zzz-integration-deletion-cleanup.spec.ts`
- `test-config-flow-soh.spec.ts` (e2e-dynamic-soc)
- `test-dynamic-soc-capping.spec.ts` (e2e-dynamic-soc)

---

## 6. Debug/Logging Noise

### 6.1 Excessive DEBUG Logging

The codebase has extensive DEBUG-level logging that may need cleanup:

| File | DEBUG log lines |
|------|----------------|
| `calculations.py` | 21 lines |
| `emhass_adapter.py` | 28 lines |
| `coordinator.py` | 9 lines |
| `trip_manager.py` | 17 lines |
| `sensor.py` | 10 lines |
| `services.py` | 5 lines |

These include `DEBUG calculate_power_profile:`, `DEBUG async_publish_all:`, `DEBUG async_delete_all_trips:`, etc.

### 6.2 E2E-DEBUG Comments

Special E2E debugging logs scattered through production code:
- `coordinator.py:105,110,156,164,199,205`
- `sensor.py:221,228,234,238,242,267,269,277`
- `services.py:1423,1425,1446,1452,1461,1466`

These are tagged `E2E-DEBUG-CRITICAL` and are used by the E2E test suite to verify behavior.

---

## 7. TODO/FIXME Comments

Only **1 active TODO** found (not counting DEBUG logs or BUG FIX comments):

- `schedule_monitor.py:190`: `# TODO: Implement proper schedule parsing` — in dead code

**"BUG FIX" comments (not actionable, just documentation):**
- `calculations.py:192`: `# BUG FIX: Frontend stores dia_semana as JS getDay() format`
- `calculations.py:257`: `# BUG FIX: hora is local time, convert to UTC`
- `calculations.py:1085`: `# BUG FIX: time_str is local time, create in local tz and convert to UTC`
- `config_flow.py:203`: `# TODO: Make EMHASS config path configurable via HA config or environment variable`
- `emhass_adapter.py:378,468,630,689,715,770`: Multiple BUG FIX comments

---

## 8. Dashboard Directory Analysis

The `dashboard/` subdirectory contains Lovelace dashboard template files:

| File | Purpose |
|------|---------|
| `dashboard.yaml` | Base dashboard template |
| `dashboard-create.yaml` | Trip creation panel |
| `dashboard-edit.yaml` | Trip editing panel |
| `dashboard-delete.yaml` | Trip deletion panel |
| `dashboard-list.yaml` | Trip listing panel |
| `ev-trip-planner-full.yaml` | Full-featured dashboard |
| `ev-trip-planner-simple.yaml` | Simplified dashboard |
| `ev-trip-planner-{vehicle_id}.yaml` | Per-vehicle template |
| `dashboard.js` | Dashboard JS handlers |
| `ev-trip-planner-simple.js` | Simple dashboard JS |

These are loaded by `dashboard.py` during dashboard import. The YAML templates are used as data, not executed as code.

---

## 9. Frontend Directory Analysis

The `frontend/` directory serves the custom panel:

| File | Purpose |
|------|---------|
| `panel.js` | Active panel code (66,502 bytes) |
| `lit-bundle.js` | Lit Element bundle (238,877 bytes) |
| `panel.css` | Panel styles (18,628 bytes) |
| `panel.js.bak` | **Obsolete backup** |
| `panel.js.old` | **Obsolete backup** |
| `panel.js.fixed` | **Obsolete "fixed" version** |

`panel.py` references `frontend/panel.js` via `async_register_static_paths()` in `services.py:1238`.

---

## 10. Summary of Findings

### Tier A — Must Fix (Architecture)

1. **`schedule_monitor.py` (327 LOC)** — Confirmed dead code. Not imported from anywhere. Delete.
2. **`EMHASSAdapter` (2,730 LOC, 41 methods)** — God class. Split into: index management, load publishing, error handling, caching.
3. **`TripManager` (2,503 LOC, 49 methods)** — God class. Split into: CRUD, SOC calculations, power profile, schedule generation.
4. **`services.py` (1,635 LOC, 0 classes, 27 functions)** — SRP violation. Group into service handler classes, dashboard helpers, cleanup utilities.
5. **3 circular import cycles** — Especially `trip_manager <-> vehicle_controller <-> presence_monitor`.

### Tier B — Should Fix (Maintenance)

6. **14 `*.cover` files** — Move to `_docs/` or add to `.gitignore`.
7. **3 frontend backup files** — `panel.js.bak`, `panel.js.old`, `panel.js.fixed`.
8. **6 high-arity functions** — Parameter lists of 8-12 violate readability.
9. **3 flat test directories** — Separate unit/, integration/, e2e/.
10. **8 orphaned bug-finding test files** — Consolidate or document.
11. **Multiple DEBUG/E2E-DEBUG logs** — Create a debug mode flag to suppress.

### Tier C — Consider (Nice to Have)

12. **`calculations.py` (1,690 LOC)** — Split into domain-specific calculators.
13. **`dashboard/` YAML templates** — Consider migrating to JSON or template engine.
14. **Strategy pattern underutilized** in `vehicle_controller.py` (5 strategies, 2 active).
