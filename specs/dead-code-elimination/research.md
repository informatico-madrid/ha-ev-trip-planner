# Research: Dead Code Elimination

## Summary

A dead code audit of the ha-ev-trip-planner codebase found **~30 actionable dead code items** after filtering out false positives. The codebase is healthy — dead code was left behind by two recent refactors (SOLID decomposition and high-arity wrapping), not by new development.

## Verified Dead Code

### A. EMHASSAdapter — Dead Public Methods (safe to remove)

| Method | Lines | Risk |
|--------|-------|------|
| `async_notify_error` | adapter.py:222-230 | Low |
| `calculate_deferrable_parameters` | adapter.py:610-621 (returns `{}`) | Low |
| `get_assigned_index` | adapter.py:207-209 | Low |
| `get_all_assigned_indices` | adapter.py:211-213 | Low |
| `async_release_trip_index` | adapter.py:176-186 (tests only) | Low |
| `async_save` | adapter.py:164-166 (tests only) | Low |
| `async_save_trips` (EMHASS version) | adapter.py:606-608 (tests only) | Low |

### B. EMHASSAdapter — Dead Attributes

| Attribute | Lines | Notes |
|-----------|-------|-------|
| `_stored_battery_capacity_kwh` | 133 | Set once, never read |
| `_stored_t_base` | 146 | Set to None, never read |
| `_stored_soh_sensor` | 147 | Set to None, never read |
| `_stored_charging_power_kw` | 132, 145 | Bug: overwritten to None immediately |

### C. IndexManager — Dead Method

| Method | Lines | Notes |
|--------|-------|-------|
| `async_release_index` | index_manager.py:63-69 (tests only) | `async_load_index` and `async_save_index` are no-op stubs but actively called from adapter.py |

### D. trip/ Package

| Item | Location | Risk |
|------|----------|------|
| `_get_all_active_trips` | _emhass_sync.py:117-127 (tests only) | Low |
| `trip_manager.py` shim | Top-level (1 TYPE_CHECKING consumer) | Medium — requires consumer update first |

### E. sensor/ — Dead Re-exports

| Item | Location |
|------|----------|
| `TRIP_SENSORS` re-export | sensor/__init__.py:14,31 |
| `_async_create_trip_sensors` re-export | sensor/__init__.py:15 |

### F. services/ — Dead Shim Files

| File | Size | Consumers |
|------|------|-----------|
| `services/handlers.py` | 205 bytes | tests only |
| `services/_lookup.py` | 197 bytes | tests only |
| `services/presence.py` | 195 bytes | tests only |

### G. Trivial Cleanup

| Item | Location |
|------|----------|
| Empty `dashboard/` directory | Only `__pycache__/` |
| Frontend backups | `panel.js.bak` (24KB), `panel.js.old` (24KB), `panel.js.fixed` (80KB) |

## NOT Dead (Kept)

- **ErrorHandler class** — Used internally by adapter methods (`handle_error`, `handle_index_error`, etc.)
- **`IndexManager.async_load_index` / `async_save_index`** — No-op stubs but called from adapter.py:162, 166, 608
- **IndexManagerBase / LoadPublisherBase** — Markers for SOLID metrics
- **`_LoadPublisherConfig`** — Type alias used in codebase
- **`async_generate_power_profile` / `async_generate_deferrables_schedule`** — Comments only, not actual methods
- **`_EmhassCtx.schema_description`** — Passed when constructing context, consumed by callers
- **`self._data` in main.py** — Part of HA ConfigFlow pattern

## Safe Removal Order

### Phase 1 — Zero Risk (pure dead code, no consumers)
1. Frontend backup files (3 files)
2. Dashboard empty directory
3. Dead attributes: `_stored_battery_capacity_kwh`, `_stored_t_base`, `_stored_soh_sensor`
4. Dead methods: `async_notify_error`, `calculate_deferrable_parameters`, `get_assigned_index`, `get_all_assigned_indices`
5. Dead methods: `async_release_trip_index`, `async_save`, `async_save_trips` (EMHASS)
6. Dead method: `async_release_index` (IndexManager)
7. Dead `__all__` entries in sensor/__init__.py

### Phase 2 — Low Risk (test consumers only)
8. Remove test references to dead methods in test_emhass_package.py
9. Remove service shim files + test consumers

### Phase 3 — Medium Risk (requires update)
10. Remove `_get_all_active_trips` (update tests first)
11. Update `vehicle/controller.py` TYPE_CHECKING import: `..trip_manager` → `..trip`
12. Remove `trip_manager.py` shim

## Quality Commands

- Lint: `make lint`
- TypeCheck: `make typecheck`
- Dead Code: `python3 -m vulture`
- Unit Test: `make test`
- Quality Gate CI: `make quality-gate-ci`
- Full Quality Gate: `make quality-gate`

## Sources

- `custom_components/ev_trip_planner/emhass/adapter.py` — EMHASSAdapter facade (1122 lines)
- `custom_components/ev_trip_planner/emhass/error_handler.py` — ErrorHandler (110 lines)
- `custom_components/ev_trip_planner/emhass/index_manager.py` — IndexManager + markers (121 lines)
- `custom_components/ev_trip_planner/emhass/load_publisher.py` — LoadPublisher + markers (364 lines)
- `custom_components/ev_trip_planner/trip/_emhass_sync.py` — EMHASSSync (128 lines)
- `custom_components/ev_trip_planner/trip_manager.py` — Backward-compat shim (5 lines)
- `custom_components/ev_trip_planner/sensor/__init__.py` — Re-exports (43 lines)
- `custom_components/ev_trip_planner/services/handlers.py` — Shim (7 lines)
- `custom_components/ev_trip_planner/services/_lookup.py` — Shim (7 lines)
- `custom_components/ev_trip_planner/services/presence.py` — Shim (7 lines)
- `custom_components/ev_trip_planner/diagnostics.py` — Uses get_available_indices
- `custom_components/ev_trip_planner/vehicle/controller.py` — TYPE_CHECKING TripManager import
- Makefile — Quality gate commands
