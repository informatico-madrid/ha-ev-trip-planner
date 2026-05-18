# Requirements: Dead Code Elimination

## Goal

Remove all verified dead code left behind by the SOLID decomposition and high-arity wrapping refactors, restoring the codebase to a clean state where every public API and attribute is actively consumed.

## User Stories

### US-1: Remove Dead EMHASSAdapter Methods
**As a** developer maintaining the adapter
**I want to** remove public methods that are no longer called by production code
**So that** the adapter surface area is minimal and the SOLID decomposition is complete

**Acceptance Criteria:**
- [ ] AC-1.1: `async_notify_error` is removed from EMHASSAdapter
- [ ] AC-1.2: `calculate_deferrable_parameters` is removed from EMHASSAdapter (the pure-function replacement lives in `calculations/schedule.py`)
- [ ] AC-1.3: `get_assigned_index` is removed from EMHASSAdapter
- [ ] AC-1.4: `get_all_assigned_indices` is removed from EMHASSAdapter
- [ ] AC-1.5: `async_release_trip_index` is removed from EMHASSAdapter
- [ ] AC-1.6: `async_save` is removed from EMHASSAdapter
- [ ] AC-1.7: `async_save_trips` (EMHASSAdapter version at line 606) is removed

### US-2: Clean Up Dead EMHASSAdapter Attributes
**As a** developer reading the adapter init
**I want to** remove attributes that are assigned but never read
**So that** the initialization logic is not misleading and the duplicate-declaration bug is fixed

**Acceptance Criteria:**
- [ ] AC-2.1: `_stored_battery_capacity_kwh` assignment and declaration are removed
- [ ] AC-2.2: `_stored_t_base` declaration is removed
- [ ] AC-2.3: `_stored_soh_sensor` declaration is removed
- [ ] AC-2.4: The duplicate declaration of `_stored_charging_power_kw` at line 145 is removed (the initial assignment at line 132 is the only survivor)

### US-3: Remove Dead IndexManager Method
**As a** developer reading the index manager
**I want to** remove `async_release_index` which has no production consumers
**So that** the async/sync split in IndexManager is not confusing

**Acceptance Criteria:**
- [ ] AC-3.1: `async_release_index` is removed from IndexManager
- [ ] AC-3.2: `async_load_index` and `async_save_index` are KEPT (no-op stubs actively called from adapter.py)

### US-4: Remove Dead trip/_emhass_sync Method
**As a** developer maintaining the trip package
**I want to** remove `_get_all_active_trips` which is only exercised by tests
**So that** the EMHASS sync module exposes only production methods

**Acceptance Criteria:**
- [ ] AC-4.1: `_get_all_active_trips` is removed from `_emhass_sync.py`

### US-5: Remove trip_manager.py Backward-Compat Shim
**As a** developer maintaining imports
**I want to** replace the TYPE_CHECKING import in vehicle/controller.py and remove the shim
**So that** there is no indirection between the public TripManager and its new home in the trip package

**Acceptance Criteria:**
- [ ] AC-5.1: `vehicle/controller.py` TYPE_CHECKING import is updated from `..trip_manager` to `..trip`
- [ ] AC-5.2: `trip_manager.py` shim file is removed
- [ ] AC-5.3: All test imports of `trip_manager.TripManager` are updated to `trip.TripManager`

### US-6: Remove Dead Re-exports from sensor/__init__.py
**As a** developer reading the sensor package __init__
**I want to** remove `TRIP_SENSORS` and `_async_create_trip_sensors` from the re-exports and __all__
**So that** the sensor package does not expose names no external code depends on

**Acceptance Criteria:**
- [ ] AC-6.1: `TRIP_SENSORS` is removed from the import block and __all__ in sensor/__init__.py
- [ ] AC-6.2: `_async_create_trip_sensors` is removed from the import block and __all__ in sensor/__init__.py

### US-7: Remove Dead Service Shim Files and Their Tests
**As a** developer maintaining the services directory
**I want to** remove the three shim files and their test consumers
**So that** the services directory contains only production code

**Acceptance Criteria:**
- [ ] AC-7.1: `services/handlers.py` is removed
- [ ] AC-7.2: `services/_lookup.py` is removed
- [ ] AC-7.3: `services/presence.py` is removed
- [ ] AC-7.4: Import references in `test_services_shims.py` and `test_services_pkg.py` are removed or the test files are removed if they become empty

### US-8: Remove Trivial Artifacts
**As a** developer cleaning up the repo
**I want to** remove frontend backup files and empty directories
**So that** the repository does not contain stale artifacts

**Acceptance Criteria:**
- [ ] AC-8.1: `panel.js.bak`, `panel.js.old`, `panel.js.fixed` are removed
- [ ] AC-8.2: Empty `dashboard/` directory (and its `__pycache__/`) is removed

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Remove 7 dead methods from EMHASSAdapter | High | `vulture --min-confidence 80 custom_components/ev_trip_planner/emhass/adapter.py` reports zero findings for removed names; tests pass |
| FR-2 | Remove 3 dead attributes + fix 1 duplicate declaration from EMHASSAdapter | High | `vulture` reports zero findings for dead attributes; no lint errors on adapter.py |
| FR-3 | Remove `async_release_index` from IndexManager | High | `vulture` reports zero findings; tests that called this method are updated |
| FR-4 | Remove `_get_all_active_trips` from trip/_emhass_sync | High | Function removed; tests calling it via `_emhass_sync._get_all_active_trips` updated or removed |
| FR-5 | Redirect TYPE_CHECKING import in vehicle/controller.py and remove trip_manager.py shim | Medium | `pyright` passes; no import errors when running the module |
| FR-6 | Remove dead re-exports from sensor/__init__.py | Medium | `vulture` reports zero findings; all existing imports continue to work (they import from `_async_setup.py` directly) |
| FR-7 | Remove 3 dead service shim files | Medium | Files removed; their test consumers in `test_services_shims.py` and `test_services_pkg.py` cleaned up |
| FR-8 | Remove frontend backups and empty dashboard directory | Low | Files and directory gone; no build step references them |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test coverage | pytest exit code | 0 (all tests green) |
| NFR-2 | Lint compliance | ruff + pylint | Zero new issues |
| NFR-3 | Type checking | pyright errors | Zero new errors |
| NFR-4 | Dead code audit | vulture findings (>=80% confidence) | Zero new findings for removed items; no new findings introduced |
| NFR-5 | No regression | production API surface | All production import paths that existed before must still resolve |

## Glossary

- **Dead code**: Code that is defined but never called/read by production code. Test-only consumers do not count as live consumers.
- **Shim**: A thin wrapper or re-export module whose sole purpose is backward compatibility, typically forwarding to the real implementation.
- **Backward-compat import**: Import kept via `if TYPE_CHECKING` or re-export for existing import paths that may still resolve.
- **No-op stub**: A method that exists (does nothing) but is actively called from production code. Not dead code — do not remove.

## Out of Scope

- **ErrorHandler class** — Used internally by all adapter error-handling methods
- **IndexManager.async_load_index / async_save_index** — No-op stubs actively called from adapter.py:162, 166, 608
- **IndexManagerBase / LoadPublisherBase** — ABC markers used for SOLID metrics collection
- **_LoadPublisherConfig** — Type alias actively used in codebase
- **calculations/schedule.py.calculate_deferrable_parameters** — This is the live pure-function replacement; DO NOT remove
- **async_generate_power_profile / async_generate_deferrables_schedule** — Comments only, not actual methods (already not present)
- **_EmhassCtx.schema_description** — Used during context construction
- **Any production import path** that currently resolves must continue to resolve after removal

## Dependencies

- None. This spec is fully self-contained within the existing codebase.
- Precondition: All prior refactors (SOLID decomposition, high-arity wrapping) are complete and tests are green before starting.

## Success Criteria

- `vulture --min-confidence 80 custom_components/` reports zero new dead-code findings after removal
- `make test` passes with zero failures and zero new warnings
- `make lint` and `make typecheck` pass cleanly
- `make quality-gate-ci` passes

## Verification Contract

**Project type**: library

**Entry points**:
- `custom_components/ev_trip_planner/emhass/adapter.py` — EMHASSAdapter class (methods removed)
- `custom_components/ev_trip_planner/emhass/index_manager.py` — IndexManager class (method removed)
- `custom_components/ev_trip_planner/trip/_emhass_sync.py` — _EmhassSync class (method removed)
- `custom_components/ev_trip_planner/trip_manager.py` — shim file (removed)
- `custom_components/ev_trip_planner/sensor/__init__.py` — re-exports (entries removed)
- `custom_components/ev_trip_planner/services/{handlers, _lookup, presence}.py` — shim files (removed)
- `custom_components/ev_trip_planner/panel.js.{bak,old,fixed}` — frontend backups (removed)
- `custom_components/ev_trip_planner/dashboard/` — empty directory (removed)

**Observable signals**:
- PASS: `vulture --min-confidence 80 custom_components/` exits with zero findings for all removed names
- PASS: `make test` exits 0, all test files pass
- PASS: `make lint` and `make typecheck` report zero issues
- FAIL: Any test that references a removed method/function/attribute fails with AttributeError or NameError
- FAIL: `import custom_components.ev_trip_planner.sensor` or `import custom_components.ev_trip_planner.trip_manager` fails (backward-compat import paths broken)

**Hard invariants**:
- `from custom_components.ev_trip_planner.sensor import async_setup_entry, TripSensor, TripPlannerSensor, EmhassDeferrableLoadSensor, TripEmhassSensor` must still work (HA platform entry point)
- `from custom_components.ev_trip_planner.trip import TripManager` must still work (public API)
- `IndexManager.async_load_index` and `async_save_index` must remain as no-op stubs
- `ErrorHandler` class must remain intact (internal consumers)
- `calculations/schedule.py.calculate_deferrable_parameters` must remain (live replacement)

**Seed data**:
- Clean git working tree with all prior refactor changes committed
- `make test` must be green before starting (baseline)
- `vulture --min-confidence 80 custom_components/` must produce a baseline output

**Dependency map**:
- `vehicle/controller.py` TYPE_CHECKING import — the only non-test consumer of `trip_manager.TripManager`
- `test_emhass_package.py` — tests dead methods (async_release_trip_index, async_save, async_save_trips, async_release_index)
- `test_trip_crud_execution.py` — tests `_get_all_active_trips`
- `test_trip_manager_properties.py` — tests `_get_all_active_trips`
- `test_services_shims.py` and `test_services_pkg.py` — test dead shim imports
- `conftest.py` (unit + integration) — imports `trip_manager.TripManager` for fixtures

**Escalate if**:
- Any removal causes an `AttributeError` or `ImportError` in production code (not tests)
- `pyright` reports type errors in files outside the removal scope
- `vulture` flags additional dead code beyond the scoped items — this is expected but should be logged for a future pass
- The `sensor/__init__.py` removal breaks HA's entity platform loading — unlikely but verify by inspection that HA loads via `platforms = ["sensor"]` manifest entry, not via __init__ imports
