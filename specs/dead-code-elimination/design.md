# Design: Dead Code Elimination

## Overview

Remove ~30 verified dead code items (methods, attributes, shims, artifacts) left behind by SOLID decomposition and high-arity wrapping refactors. Three-phase, zero-to-medium risk, with test consumers updated before source files are removed.

## Architecture

```mermaid
graph TB
    subgraph Source["Source Files (Modified/Deleted)"]
        A[emhass/adapter.py]
        B[emhass/index_manager.py]
        C[trip/_emhass_sync.py]
        D[vehicle/controller.py]
        E[sensor/__init__.py]
        F[services/handlers.py]
        G[services/_lookup.py]
        H[services/presence.py]
        I[trip_manager.py]
        J[panel.js.* + dashboard/]
    end

    subgraph TestFiles["Test Consumers (Updated)"]
        T1[test_emhass_package.py]
        T2[test_trip_crud_execution.py]
        T3[test_trip_manager_properties.py]
        T4[test_services_pkg.py]
        T5[test_services_shims.py]
        T6[unit/conftest.py]
        T7[integration/conftest.py]
    end

    subgraph Kept["Preserved (NOT Dead)"]
        K1[ErrorHandler]
        K2[IndexManager.async_load_index]
        K3[IndexManager.async_save_index]
        K4[calculations/schedule.py.calculate_deferrable_parameters]
        K5[TripManager (trip/manager.py)]
        K6[TripManager (trip/__init__.py re-export)]
        K7[get_available_indices]
    end

    A --- T1
    B --- T1
    C --- T2
    C --- T3
    D --- T6
    D --- T7
    E --- T4
    F --- T4
    F --- T5
    G --- T4
    H --- T4
    I --- T6
    I --- T7
```

## Components

### Component 1: EMHASSAdapter Dead Code
**Purpose**: Remove 7 dead methods + 3 dead attributes + 1 duplicate declaration from adapter.py
**Requirements**: US-1/FR-1 (dead methods), US-2/FR-2 (dead attributes)

**Methods to remove**:
| Method | Lines | Rationale |
|--------|-------|-----------|
| `async_notify_error` | 222-230 | Zero consumers (prod + test) |
| `calculate_deferrable_parameters` | 610-621 | Returns `{}`, replacement lives in `calculations/schedule.py` |
| `get_assigned_index` | 207-209 | Dead, `get_available_indices` (line 215) is live (consumed by `diagnostics.py`) |
| `get_all_assigned_indices` | 211-213 | Dead |
| `async_release_trip_index` | 176-186 | Test-only consumer |
| `async_save` | 164-166 | Test-only consumer |
| `async_save_trips` (EMHASS version) | 606-608 | Test-only consumer |

**Attributes to remove**:
| Attribute | Lines | Rationale |
|-----------|-------|-----------|
| `_stored_battery_capacity_kwh` | 133 | Assigned but never read |
| `_stored_t_base` | 146 | Set to None, never read |
| `_stored_soh_sensor` | 147 | Set to None, never read |
| `_stored_charging_power_kw` (dup) | 145 | Duplicate declaration — overwrites line 132's value with None. Keep line 132, remove 145. |

### Component 2: IndexManager Dead Method
**Purpose**: Remove `async_release_index` from index_manager.py
**Requirements**: US-3/FR-3

| Method | Lines | Rationale |
|--------|-------|-----------|
| `async_release_index` | 63-69 | Test-only consumer (test_emhass_package.py) |

**Preserved**: `async_load_index` (line 71), `async_save_index` (line 75) — no-op stubs actively called from adapter.py:162, 166, 608.

### Component 3: trip/_emhass_sync Dead Method
**Purpose**: Remove `_get_all_active_trips` from _emhass_sync.py
**Requirements**: US-4/FR-4

| Method | Lines | Rationale |
|--------|-------|-----------|
| `_get_all_active_trips` | 117-127 | Only test consumers |

### Component 4: vehicle/controller.py TYPE_CHECKING
**Purpose**: Update TYPE_CHECKING import from `..trip_manager` to `..trip`
**Requirements**: US-5/FR-5 (shared with Component 7 — controller import update is a prerequisite for trip_manager.py shim deletion)

| File | Change |
|------|--------|
| `vehicle/controller.py:26` | `from ..trip_manager import TripManager` → `from ..trip import TripManager` |

### Component 5: sensor/__init__.py Dead Re-exports
**Purpose**: Remove `TRIP_SENSORS` and `_async_create_trip_sensors` from imports and `__all__`
**Requirements**: US-6/FR-6

| Item | Import Line | `__all__` Line |
|------|-------------|----------------|
| `TRIP_SENSORS` | 14 | 31 |
| `_async_create_trip_sensors` | 15 | Removed (not in `__all__`) |

### Component 6: Service Shim Files
**Purpose**: Delete 3 shim files + their test consumers
**Requirements**: US-7/FR-7

| File | Size |
|------|------|
| `services/handlers.py` | 205 bytes |
| `services/_lookup.py` | 197 bytes |
| `services/presence.py` | 195 bytes |

### Component 7: trip_manager.py Shim
**Purpose**: Update all test imports then delete the shim
**Requirements**: US-5/FR-5 (shared with Component 4 — shim deletion completes the same user story)

| Consumer | Path |
|----------|------|
| `unit/conftest.py:11` | `from custom_components.ev_trip_planner.trip_manager import TripManager` |
| `unit/conftest.py:867` | `from custom_components.ev_trip_planner.trip_manager import TripManager` |
| `integration/conftest.py:635` | `from custom_components.ev_trip_planner.trip_manager import TripManager` |
| `integration/conftest.py:658` | `from custom_components.ev_trip_planner.trip_manager import TripManager` |

### Component 8: Frontend Backups + Empty Directory
**Purpose**: Remove stale artifacts
**Requirements**: US-8/FR-8

| Item | Path | Notes |
|------|------|-------|
| `panel.js.bak` | `custom_components/ev_trip_planner/` | Does not exist (already cleaned?) — skip if absent |
| `panel.js.old` | `custom_components/ev_trip_planner/` | Does not exist — skip |
| `panel.js.fixed` | `custom_components/ev_trip_planner/` | Does not exist — skip |
| `dashboard/` | `custom_components/ev_trip_planner/dashboard/` | Exists, only contains `__pycache__/` |

## Technical Decisions

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Removal order | Parallel vs sequential | Sequential phases | Each phase must pass tests/lint before next — dead code removals are interdependent (shim deletion depends on import update) |
| Test file cleanup | Delete vs patch | Patch | Test files test real production code; deleting them loses coverage signal. Patch removes dead references, keep file for other valid tests |
| trip_manager.py deletion | Keep as TYPE_CHECKING-only shim | Delete | After updating controller.py and all test imports, the shim has zero consumers. No backward compat needed — `trip_manager` is not a documented public API |
| Frontend backup handling | rm -f vs conditional | Conditional | Files may already be gone from this branch (git state shows no panel.js* files) — use `rm -f` to be idempotent |
| Dashboard directory | Remove vs keep empty | Remove + parent check | Only contains `__pycache__/`. Remove `__pycache__/` then `rmdir dashboard/` |

## File Structure Changes

| File | Action | Purpose |
|------|--------|---------|
| `custom_components/ev_trip_planner/emhass/adapter.py` | Modify | Remove 7 dead methods, 3 dead attrs + 1 duplicate |
| `custom_components/ev_trip_planner/emhass/index_manager.py` | Modify | Remove `async_release_index` (lines 63-69) |
| `custom_components/ev_trip_planner/trip/_emhass_sync.py` | Modify | Remove `_get_all_active_trips` (lines 117-127) |
| `custom_components/ev_trip_planner/vehicle/controller.py` | Modify | Update TYPE_CHECKING import: `..trip_manager` → `..trip` |
| `custom_components/ev_trip_planner/sensor/__init__.py` | Modify | Remove `TRIP_SENSORS` + `_async_create_trip_sensors` from imports and `__all__` |
| `custom_components/ev_trip_planner/services/handlers.py` | Delete | Dead shim file |
| `custom_components/ev_trip_planner/services/_lookup.py` | Delete | Dead shim file |
| `custom_components/ev_trip_planner/services/presence.py` | Delete | Dead shim file |
| `custom_components/ev_trip_planner/trip_manager.py` | Delete | Dead shim file |
| `custom_components/ev_trip_planner/panel.js.bak` | Delete | Stale artifact (may not exist — use rm -f) |
| `custom_components/ev_trip_planner/panel.js.old` | Delete | Stale artifact (may not exist — use rm -f) |
| `custom_components/ev_trip_planner/panel.js.fixed` | Delete | Stale artifact (may not exist — use rm -f) |
| `custom_components/ev_trip_planner/dashboard/` | Delete | Empty directory (remove __pycache__ first) |
| `tests/unit/test_emhass_package.py` | Modify | Remove tests for dead methods (7 test methods total) |
| `tests/unit/test_trip_crud_execution.py` | Modify | Remove `TestGetAllActiveTrips` class + all 4 test methods |
| `tests/unit/test_trip_manager_properties.py` | Modify | Remove `test_get_all_active_trips_via_emhass_sync` test method |
| `tests/integration/test_services_pkg.py` | Modify | Remove 3 shim test classes (~52 lines total) |
| `tests/integration/test_services_shims.py` | Modify | Remove all 3 test methods for dead shims |
| `tests/unit/conftest.py` | Modify | Update 2 imports: `trip_manager` → `trip` |
| `tests/integration/conftest.py` | Modify | Update 2 imports: `trip_manager` → `trip` |

## Implementation Sequence

### Phase 1 — Zero Risk (remove dead code, no consumers)

1. **Remove `dashboard/__pycache__/`** and `rmdir custom_components/ev_trip_planner/dashboard/`
2. **Remove frontend backups**: `rm -f panel.js.bak panel.js.old panel.js.fixed` (idempotent, may not exist)
3. **Remove dead attributes** from `adapter.py`:
   - Line 133: `self._stored_battery_capacity_kwh = battery_capacity_kwh`
   - Line 146: `self._stored_t_base: float | None = None`
   - Line 147: `self._stored_soh_sensor: str | None = None`
   - Line 145 (duplicate): `self._stored_charging_power_kw: float | None = None`
4. **Remove dead methods** from `adapter.py`:
   - `async_notify_error` (lines 222-230)
   - `calculate_deferrable_parameters` (lines 610-621)
   - `get_assigned_index` (lines 207-209)
   - `get_all_assigned_indices` (lines 211-213)
   - `async_release_trip_index` (lines 176-186)
   - `async_save` (lines 164-166)
   - `async_save_trips` at line 606 (EMHASS version, NOT the TripPersistence one)
5. **Remove `async_release_index`** from `index_manager.py` (lines 63-69)
6. **Remove dead re-exports** from `sensor/__init__.py`:
   - Remove `TRIP_SENSORS` from import line 14 and `__all__` entry line 31
   - Remove `_async_create_trip_sensors` from import line 15
7. **Clean test_emhass_package.py**: Remove tests for the dead methods removed in steps 4-5 (lands atomically with the source removals):
   - `test_async_release_index_*` (2 tests)
   - `test_async_save_*` (1 test)
   - `test_async_release_trip_index_*` (2 tests)
   - `test_get_assigned_index*` (2 tests)
   - `test_get_all_assigned_indices` (1 test)
   - `test_async_notify_error_logs` (1 test)
   - `test_calculate_deferrable_parameters_returns_empty` (1 test)
   - `test_async_save_trips_delegates` (1 test)
8. **Verify**: `make test` passes (green-test invariant must hold at every phase boundary; `make test` also runs lint-relevant checks)

### Phase 2 — Low Risk (delete shim files + update test consumers)

9. **Delete shim files**: `rm services/handlers.py services/_lookup.py services/presence.py`
10. **Clean test_services_shims.py**: Remove all 3 test methods (or remove file if empty)
11. **Clean test_services_pkg.py**: Remove `TestServicesLookupShim`, `TestServicesPresenceShim`, `TestServicesHandlersShim` classes
12. **Verify**: `make test` passes

### Phase 3 — Medium Risk (update imports, then delete shim, update remaining tests)

13. **Update `vehicle/controller.py:26`**: `from ..trip_manager import TripManager` → `from ..trip import TripManager`
14. **Update test imports**: `tests/unit/conftest.py` (lines 11, 867) and `tests/integration/conftest.py` (lines 635, 658): `trip_manager` → `trip`
15. **Delete `trip_manager.py`** shim
16. **Update test consumers** of `_get_all_active_trips`:
    - Remove `TestGetAllActiveTrips` class (4 tests) from `test_trip_crud_execution.py`
    - Remove `test_get_all_active_trips_via_emhass_sync` from `test_trip_manager_properties.py`
17. **Delete `_get_all_active_trips`** from `_emhass_sync.py` (lines 117-127)
18. **Verify**: `make test` passes

### Phase 4 — Verification (final gate)

19. **Run full verification suite**:
    - `make lint` — ruff + pylint clean
    - `make typecheck` — pyright clean
    - `make dead-code` — vulture reports zero new findings for removed names
    - `make test` — all tests pass
    - `make quality-gate-ci` — CI quality gate passes
20. **Verify hard invariants**:
    - `from custom_components.ev_trip_planner.sensor import async_setup_entry, TripSensor, TripPlannerSensor, EmhassDeferrableLoadSensor, TripEmhassSensor` still works
    - `from custom_components.ev_trip_planner.trip import TripManager` still works
    - `IndexManager.async_load_index` and `async_save_index` still present
    - `ErrorHandler` class still intact
    - `calculations/schedule.py.calculate_deferrable_parameters` still present

## Error Handling

| Error Scenario | Detection | Mitigation |
|----------------|-----------|------------|
| `AttributeError` after method removal | `make test` fails with AttributeError | Check grep for missed consumers; if found in production code, escalate |
| `ImportError` after shim deletion | Python import fails | Verify all consumers updated before deleting shim; revert if needed |
| `pyright` type errors | `make typecheck` fails | Verify controller.py TYPE_CHECKING block updated; check for other TripManager imports |
| `vulture` still reports removed names as alive | `make dead-code` passes (false) | Verify lines were actually removed; vulture confidence threshold |
| `vulture` flags NEW dead code | New findings beyond scoped items | Expected — log for future pass, not in scope |
| `test_emhass_package.py` test count drops significantly | Expected | Document the count reduction; no regression signal |

## Test Strategy

### Test Double Policy

This is a removal spec — no new test doubles are created. Existing test infrastructure (pytest fixtures, mock Store instances, mock Hass instances) is used to verify that removals are safe and that tests remain green after updates.

### Mock Boundary

| Component | Unit test | Integration test | Rationale |
|---|---|---|---|
| EMHASSAdapter (dead methods) | N/A — tests removed | N/A — tests removed | Tests for dead methods are deleted, not updated |
| IndexManager.async_release_index | N/A — test removed | N/A — test removed | Test deleted; remaining IndexManager methods keep their existing tests |
| _EmhassSync._get_all_active_trips | N/A — tests removed | N/A — tests removed | Test classes deleted; remaining EMHASSSync tests preserved |
| TripManager imports (conftest fixtures) | Real | Real | No double needed — fixture creation is the observable outcome |
| Sensor re-exports | N/A — imports removed | N/A — imports removed | Dead re-exports tested by import assertion tests; tests deleted |

### Fixtures & Test Data

| Component | Required state | Form |
|---|---|---|
| trip_manager_with_entry_id (unit/conftest.py) | mock_hass, mock_store, valid entry | Fixture fn at line 865 — update import path |
| mock_hass_manager_setup_error (integration/conftest.py) | mock_hass with entry.runtime_data.trip_manager = None | Fixture at line 628 — update import path |
| mock_hass_manager_setup_ok (integration/conftest.py) | Same as above, async_setup succeeds | Fixture at line 651 — update import path |

### Test Coverage Table

| Component / Function | Test type | What to assert | Test double |
|---|---|---|---|
| EMHASSAdapter (remaining methods) | unit | Existing tests still pass, no AttributeError | none (tests preserved) |
| IndexManager (remaining methods) | unit | async_assign_index, release_index, async_load/save_index still work | none |
| _EmhassSync (remaining methods) | unit | _async_sync_trip_to_emhass, _async_remove_trip_from_emhass, _async_publish_new_trip_to_emhass still work | none |
| VehicleController | unit | TYPE_CHECKING import resolves correctly, class instantiates | none |
| sensor/__init__.py | unit | HA entry point imports resolve (async_setup_entry, TripSensor, etc.) | none |
| TripManager import path | unit | `from custom_components.ev_trip_planner.trip import TripManager` resolves | none |
| vulture dead code check | static | Zero findings for: async_notify_error, calculate_deferrable_parameters, get_assigned_index, get_all_assigned_indices, async_release_trip_index, async_save, async_save_trips (EMHASS), async_release_index, _get_all_active_trips, TRIP_SENSORS, _async_create_trip_sensors, handlers, _lookup, presence | none |

### Test File Conventions

- Test runner: **pytest** (via `python3 -m pytest` or `.venv/bin/python -m pytest`)
- Test file location: **co-located `tests/unit/` and `tests/integration/`**
- Test pattern: `test_*.py` files in tests/unit/ and tests/integration/
- Async tests: `@pytest.mark.asyncio` decorator
- Mock cleanup: `unittest.mock.AsyncMock`, `MagicMock` — no explicit mockClear (pytest creates fresh instances per test)
- Fixture/factory location: `tests/unit/conftest.py` and `tests/integration/conftest.py`

## Performance Considerations

- No performance impact — this is code removal only
- Removing dead code reduces module size slightly (adapter.py: ~1122 lines → ~1075 lines)
- Removing unused attributes reduces instance memory by ~0 bytes (values were never assigned meaningful data)

## Security Considerations

- No security impact — dead code removal does not change any security surface
- Ensure removed methods were not being called by external integrations (verified: zero production consumers)
- The `services/` shim file removal should not break any external service calls — these shims only re-exported from `_utils.py`, which remains intact

## Existing Patterns to Follow

- **pytest-based testing**: All tests use `pytest.mark.asyncio` for async tests, `AsyncMock` for mock Store
- **Fixture pattern**: conftest.py files define reusable fixtures; tests consume via function parameter
- **Import style**: `from custom_components.ev_trip_planner.trip import TripManager` (full package path)
- **Code quality gates**: `make lint`, `make typecheck`, `make dead-code`, `make test` — all must pass

## Unresolved Questions

- **panel.js* files**: Grep confirms they do not exist in this branch (already removed in a prior commit or never created on this branch). The design assumes `rm -f` is idempotent. If they were supposed to exist but don't, this is not a regression (the spec goal is to ensure they are absent).
- **test_trip_imports.py**: Imports from `trip.manager` directly, not from `trip_manager`. Does not need updating. Verified no consumer changes needed.

## Implementation Steps

1. Remove dashboard/__pycache__/ and rmdir dashboard/
2. rm -f panel.js.bak panel.js.old panel.js.fixed (idempotent)
3. Remove 4 dead attributes from adapter.py (lines 133, 145, 146, 147)
4. Remove 7 dead methods from adapter.py
5. Remove async_release_index from index_manager.py
6. Remove TRIP_SENSORS + _async_create_trip_sensors from sensor/__init__.py
7. Clean test_emhass_package.py (remove 11 tests for dead methods — lands atomically with steps 4-5)
8. Verify Phase 1: make test passes
9. Delete services/handlers.py, services/_lookup.py, services/presence.py
10. Update test_services_shims.py (remove 3 test methods)
11. Update test_services_pkg.py (remove 3 shim test classes)
12. Verify Phase 2: make test passes
13. Update vehicle/controller.py TYPE_CHECKING import
14. Update tests/unit/conftest.py TripManager imports (2 occurrences); update tests/integration/conftest.py TripManager imports (2 occurrences)
15. Delete trip_manager.py shim
16. Remove TestGetAllActiveTrips from test_trip_crud_execution.py; remove test_get_all_active_trips_via_emhass_sync from test_trip_manager_properties.py
17. Delete _get_all_active_trips from _emhass_sync.py
18. Verify Phase 3: make test passes
19. Run verification: lint, typecheck, dead-code, test, quality-gate-ci
