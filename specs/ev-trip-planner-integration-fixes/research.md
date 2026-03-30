---
spec: ev-trip-planner-integration-fixes
phase: research
created: 2026-03-29
---

# Research: EV Trip Planner Integration Fixes

## Executive Summary

This research analyzes 5 issues in the EV Trip Planner HA integration:
1. **Duplicate panels** due to case-insensitive URL collision (chispitas vs Chispitas)
2. **Panel flickering** from aggressive update loops in DataUpdateCoordinator
3. **Estimated energy field** should be read-only and auto-calculated
4. **Cascade delete** needed - deleting integration should remove associated trips
5. **p_deferrable index** display needed per trip for EMHASS planning

Root causes identified through code analysis. Recommendations include tests first, then fixes.

## Issue Analysis

### Issue 1: Duplicate Panel (Case Sensitivity)

**Problem**: When adding a vehicle via config flow, two panels are created with URLs differing only in case (e.g., `ev-trip-planner-chispitas` vs `ev-trip-planner-Chispitas`).

**Root Cause Analysis**:
- In `config_flow.py` line 725, `vehicle_id` is derived: `vehicle_id = vehicle_name.lower().replace(" ", "_")`
- In `config_flow.py` line 780, panel is registered with `vehicle_id=vehicle_id` (lowercased)
- In `__init__.py` line 557, panel is also registered with `vehicle_id=vehicle_id`
- **BUT**: Looking at `config_flow.py` line 725, the `vehicle_id` IS already lowercased
- The issue may be in `_async_create_entry` calling panel registration twice OR in how vehicle_id is stored in entry.data

**Code Location**:
- `config_flow.py` line 725: `vehicle_id = vehicle_name.lower().replace(" ", "_")`
- `config_flow.py` line 778-782: Panel registration in `_async_create_entry`
- `__init__.py` line 555-559: Panel registration in `async_setup_entry`
- `panel.py` line 53: `frontend_url_path = f"{PANEL_URL_PREFIX}-{vehicle_id}"`

**Likely Fix**:
- The duplicate comes from panel being registered in BOTH `_async_create_entry` (config_flow.py) AND `async_setup_entry` (__init__.py)
- Need to ensure panel is registered only once, OR use case-insensitive deduplication

### Issue 2: Panel Flickering (Aggressive Update Loop)

**Problem**: The vehicle panel updates constantly in an aggressive loop, filling the console with repetitive debug messages.

**Root Cause Analysis**:
- In `__init__.py` line 338, `update_interval=timedelta(seconds=30)` is set
- But services call `coordinator.async_refresh_trips()` which calls `async_request_refresh()` (line 373)
- Looking at the sensor.py `TripPlannerSensor.async_update()` - this is called by HA's sensor update mechanism
- The issue is likely that `async_request_refresh()` triggers `_async_update_data()` which recalculates everything, causing UI refreshes

**Code Location**:
- `__init__.py` line 322-342: `TripPlannerCoordinator` class
- `__init__.py` line 371-373: `async_refresh_trips()` method
- `sensor.py` line 62-129: `TripPlannerSensor.async_update()` - logs at DEBUG level but called frequently

**Likely Fix**:
- Add debouncing to prevent rapid successive refreshes
- Use `should_refresh` flag or timestamp tracking to throttle updates
- Consider using `HomeAssistant.async_call_later` for debouncing

### Issue 3: Estimated Energy Field (Read-Only Auto-Calculated)

**Problem**: The estimated energy field should be read-only and automatically calculated as `distance x consumption`.

**Root Cause Analysis**:
- In `trip_manager.py` line 138-160, `calcular_energia_kwh()` already exists
- In `trip_manager.py` line 932-938, `async_calcular_energia_necesaria()` uses `kwh` directly if available, otherwise calculates from `km * consumption`
- The `kwh` field in trips is user-editable but should be calculated from `km` and vehicle consumption

**Code Location**:
- `utils.py` line 138-160: `calcular_energia_kwh()` function
- `trip_manager.py` line 902-990: `async_calcular_energia_necesaria()` method
- `sensor.py` line 626-635: TripSensor stores `kwh` as user-provided value

**Likely Fix**:
- In dashboard forms, make energy field readonly and populate from `km * vehicle_consumption`
- Store `km` as primary value, calculate `kwh` on demand or cache it
- Add validation that rejects manual kwh entry if km is available

### Issue 4: Cascade Delete (Integration -> Trips)

**Problem**: When deleting an integration, associated trips are not deleted.

**Root Cause Analysis**:
- In `__init__.py` line 630-656, `async_unload_entry()` only:
  - Unloads platforms
  - Cleans up runtime data
  - Removes native panel
- **Missing**: No call to delete trips from TripManager storage

**Code Location**:
- `__init__.py` line 630-656: `async_unload_entry()` function
- `trip_manager.py` line 437-465: `async_delete_trip()` exists but not called on unload
- `trip_manager.py` line 216-258: `async_save_trips()` / `_load_trips()` handle persistence

**Likely Fix**:
- In `async_unload_entry`, before removing runtime data:
  1. Get TripManager for the vehicle
  2. Call `async_delete_all_trips()` (new method) or iterate and delete each trip
  3. This ensures HA storage is cleaned up

### Issue 5: p_deferrable Index Display

**Problem**: Each trip should show its index (0, 1, 2...) in the card since EMHASS returns planning separately for each p_deferrable.

**Root Cause Analysis**:
- In `emhass_adapter.py` line 74-111, `async_assign_index_to_trip()` assigns indices
- In `emhass_adapter.py` line 299-301, `get_assigned_index()` returns the index
- In `trip_manager.py` line 1170-1175, `trip_indices` dict is created but only stored locally in `async_generate_deferrables_schedule()`
- The index is NOT persisted with the trip data

**Code Location**:
- `emhass_adapter.py` line 74-111: Index assignment logic
- `emhass_adapter.py` line 34-36: `_index_map` stores trip_id -> index mapping
- `emhass_adapter.py` line 299-305: `get_assigned_index()` method
- `trip_manager.py` line 1170-1175: Index assigned but not stored with trip

**Likely Fix**:
- Store `emhass_index` in trip data (trip["emhass_index"])
- Display index in dashboard card
- Use `emhass_adapter.get_assigned_index(trip_id)` to retrieve when displaying

## Codebase Analysis

### Existing Patterns

| Pattern | Location | Description |
|---------|----------|-------------|
| Panel Registration | `panel.py` lines 37-124 | `async_register_panel()` with cache-busting |
| Config Entry Setup | `__init__.py` lines 424-627 | `async_setup_entry()` initializes all components |
| Trip Storage | `trip_manager.py` lines 85-161 | HA Store API for persistence |
| EMHASS Integration | `emhass_adapter.py` lines 20-450+ | Deferrable load publishing |

### Dependencies

| Dependency | Used For |
|------------|----------|
| `homeassistant.helpers.storage.Store` | Trip persistence |
| `homeassistant.components.panel_custom` | Native panel registration |
| `homeassistant.core HomeAssistant` | All integrations |
| `DataUpdateCoordinator` | Sensor data coordination |

### Constraints

1. **HA Version Compatibility**: Code must work with HA 2026.x
2. **Storage API**: Must use HA Store API not raw file I/O for persistence
3. **Config Entry Pattern**: All vehicles are config entries with unique entry_id

## Quality Commands Discovery

From `package.json`:
```bash
pnpm run lint      # ESLint for JS/TS
pnpm run check-types  # TypeScript type checking
pnpm test          # Jest tests
pnpm test:e2e      # Playwright E2E tests
```

From `Makefile`:
```bash
make test          # Run pytest
make lint          # Run pylint
make e2e           # Run E2E tests withHA
```

**Local CI**: `pnpm run lint && pnpm run check-types && pnpm test && pnpm run build`

## Verification Tooling

| Tool | Command | Detected From |
|------|---------|---------------|
| Dev Server | `npm run dev` or `ha core start` | package.json / HA |
| Browser Automation | `playwright` | devDependencies |
| E2E Config | `playwright.config.ts` | project root |
| Port | `8123` | HA default |
| Health Endpoint | Not found | Custom component |

**Project Type**: Home Assistant Custom Component (Python/TypeScript)
**Verification Strategy**: Start dev server, use playwright for critical user flows

## Recommendations for Requirements

### Issue 1 (Duplicate Panels)
1. Create test: verify single panel per vehicle_id after config flow
2. Create test: verify case-insensitive vehicle_id deduplication
3. Fix: Remove duplicate panel registration OR add case-insensitive check

### Issue 2 (Panel Flickering)
1. Create test: verify refresh throttling (no more than 1 refresh per 5 seconds)
2. Create test: verify debug log doesn't spam on each update
3. Fix: Add debounce/throttle mechanism to coordinator

### Issue 3 (Estimated Energy Read-Only)
1. Create test: verify energy auto-calculated from km x consumption
2. Create test: verify energy field is readonly in dashboard forms
3. Fix: Make energy field calculated, not user-provided

### Issue 4 (Cascade Delete)
1. Create test: verify trips deleted when integration deleted
2. Create test: verify HA storage cleaned after delete
3. Fix: Add trip cleanup to `async_unload_entry`

### Issue 5 (p_deferrable Index)
1. Create test: verify trip has emhass_index after EMHASS publish
2. Create test: verify index displayed in trip card
3. Fix: Store emhass_index in trip data and display in UI

## Open Questions

- **Q1**: Is the duplicate panel issue confirmed to be from two registration calls, or from case-sensitive URL handling in HA?
- **Q2**: Should the estimated energy calculation use cached value or calculate on-demand?
- **Q3**: Is there a need to preserve trips across re-installation of the integration, or should they be deleted with the integration?

## Sources

- `custom_components/ev_trip_planner/config_flow.py` - Config flow implementation
- `custom_components/ev_trip_planner/__init__.py` - Integration setup/uninstall
- `custom_components/ev_trip_planner/panel.py` - Panel registration
- `custom_components/ev_trip_planner/trip_manager.py` - Trip CRUD operations
- `custom_components/ev_trip_planner/emhass_adapter.py` - EMHASS integration
- `custom_components/ev_trip_planner/sensor.py` - Sensor entities
- `custom_components/ev_trip_planner/utils.py` - Utility functions
- `tests/test_panel.py` - Existing panel tests
- Home Assistant Custom Component Best Practices (internal skill reference)