# Requirements: EV Trip Planner Integration Fixes

## Goal

Fix 5 critical bugs in the EV Trip Planner Home Assistant integration: duplicate vehicle panels from case-sensitive URL handling, aggressive panel refresh loops flooding debug logs, estimated energy field allowing manual input instead of auto-calculation, orphaned trips remaining after integration deletion, and missing p_deferrable index display per trip.

## User Stories

### US-1: Duplicate Panel Prevention
**As a** vehicle owner
**I want** only one panel to be created when I add a vehicle via config flow
**So that** I do not see duplicate entries in my Home Assistant sidebar

**Acceptance Criteria:**
- [ ] AC-1.1: Adding a vehicle via config flow creates exactly one panel
- [ ] AC-1.2: Panel URL uses consistent casing (vehicle_id lowercased)
- [ ] AC-1.3: No two panels can have URLs differing only in case (e.g., `ev-trip-planner-chispitas` vs `ev-trip-planner-Chispitas`)
- [ ] AC-1.4: Existing panel with same vehicle_id is reused, not recreated
- [ ] AC-1.5: Test verifies no duplicate panels exist after config flow completes

### US-2: Panel Refresh Throttling
**As a** vehicle owner
**I want** the panel to update at reasonable intervals
**So that** my console is not flooded with repetitive debug messages

**Acceptance Criteria:**
- [ ] AC-2.1: Panel does not refresh more than once per 5-second window
- [ ] AC-2.2: Debug logs do not repeat the same message more than once per refresh cycle
- [ ] AC-2.3: User interactions (trip create/edit/delete) trigger a single refresh, not multiple
- [ ] AC-2.4: Coordinator ignores refresh requests while a refresh is already in progress
- [ ] AC-2.5: Test verifies throttling behavior with rapid successive refresh requests

### US-3: Estimated Energy Auto-Calculation
**As a** vehicle owner
**I want** the estimated energy field to be automatically calculated
**So that** I see accurate energy requirements based on distance and vehicle consumption

**Acceptance Criteria:**
- [ ] AC-3.1: Energy field displays calculated value as `distance_km * vehicle_consumption_kwh_per_100km / 100`
- [ ] AC-3.2: Energy field is read-only in the dashboard form
- [ ] AC-3.3: Energy recalculates automatically when distance changes
- [ ] AC-3.4: Energy calculation uses the vehicle's stored consumption value
- [ ] AC-3.5: Test verifies energy is correctly calculated for known distance and consumption values
- [ ] AC-3.6: Test verifies energy field cannot be manually edited in the UI

### US-4: Cascade Delete Integration
**As a** vehicle owner
**I want** all associated trips to be deleted when I remove a vehicle integration
**So that** I do not have orphaned trip data remaining in Home Assistant storage

**Acceptance Criteria:**
- [ ] AC-4.1: Deleting a vehicle integration removes all its trips from TripManager storage
- [ ] AC-4.2: HA storage is cleaned up (no orphaned trip records remain)
- [ ] AC-4.3: Trip sensors for the deleted vehicle are removed
- [ ] AC-4.4: No errors occur during cascade deletion
- [ ] AC-4.5: Test verifies trips are deleted when integration is unloaded
- [ ] AC-4.6: Test verifies HA storage contains no trips for deleted integration

### US-5: p_deferrable Index Display
**As a** vehicle owner
**I want** each trip to show its EMHASS p_deferrable index
**So that** I can identify which trips correspond to each deferrable load schedule

**Acceptance Criteria:**
- [ ] AC-5.1: Each trip card displays its p_deferrable index (0, 1, 2, ...)
- [ ] AC-5.2: Index is persisted with trip data (survives restart)
- [ ] AC-5.3: Index assignment matches EMHASS adapter's `_index_map`
- [ ] AC-5.4: Index is displayed prominently on the trip card (e.g., "Deferrable #0")
- [ ] AC-5.5: Test verifies index is stored with trip data after EMHASS publish
- [ ] AC-5.6: Test verifies index appears correctly in dashboard trip cards

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Single Panel Registration | High | Panel registered once per vehicle in `async_setup_entry`, not in `_async_create_entry` |
| FR-2 | Case-Insensitive Panel URLs | High | Use lowercased vehicle_id for all panel URLs, reject duplicate case variants |
| FR-3 | Refresh Debouncing | High | Coordinator ignores refresh requests within 5-second window using timestamp tracking |
| FR-4 | Refresh Request Coalescing | High | Multiple calls to `async_request_refresh()` during active refresh are deduplicated |
| FR-5 | Energy Read-Only Field | High | Dashboard form sets `readonly` attribute on energy input, calculation happens server-side |
| FR-6 | Energy Auto-Calculation | High | `calcular_energia_kwh()` used as primary source, called when trip distance changes |
| FR-7 | Cascade Trip Deletion | High | `async_unload_entry()` calls `async_delete_all_trips()` before removing runtime data |
| FR-8 | Trip Index Persistence | High | `emhass_index` stored in trip data structure and persisted to HA storage |
| FR-9 | Index Display in UI | High | Trip card template includes `emhass_index` field with "Deferrable #N" label |
| FR-10 | Debounce Debug Logging | Medium | Log only when refresh actually occurs, not on throttled/debounced requests |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Panel Load Time | Time from sidebar click to panel visible | < 2 seconds |
| NFR-2 | Refresh Latency | Time from data change to panel update | < 1 second after debounce window |
| NFR-3 | Memory Usage | Additional memory for panel component | < 30MB |
| NFR-4 | Console Log Volume | Debug messages per minute during idle | < 10 messages |
| NFR-5 | HA Compatibility | Home Assistant versions | 2024.x, 2025.x, 2026.x |
| NFR-6 | Storage Cleanup | Orphaned records after integration delete | 0 records |

## Test Requirements

### Unit Tests (pytest)

| Test | Coverage | Location |
|------|----------|----------|
| TU-1: Duplicate panel detection | FR-1, FR-2 | `tests/test_config_flow.py` |
| TU-2: Case-insensitive vehicle_id | FR-2 | `tests/test_config_flow.py` |
| TU-3: Refresh throttling | FR-3, FR-4 | `tests/test_coordinator.py` |
| TU-4: Energy calculation accuracy | FR-6 | `tests/test_trip_manager.py` |
| TU-5: Energy field readonly validation | FR-5 | `tests/test_dashboard.py` |
| TU-6: Cascade deletion | FR-7 | `tests/test_integration_uninstall.py` |
| TU-7: Trip index persistence | FR-8 | `tests/test_emhass_adapter.py` |
| TU-8: Debounce logging suppression | FR-10 | `tests/test_coordinator.py` |

### Integration Tests (E2E Playwright)

| Test | User Story | Flow |
|------|------------|------|
| TE-1: Single panel after vehicle add | US-1 | Config flow -> verify one panel in sidebar |
| TE-2: No duplicate panel URLs | US-1 | Add vehicle -> check no case-variant panels exist |
| TE-3: Trip create triggers single refresh | US-2 | Create trip -> verify only one debug log entry |
| TE-4: Energy field is readonly | US-3 | Open trip form -> verify energy input disabled |
| TE-5: Energy auto-updates | US-3 | Change distance -> verify energy recalculates |
| TE-6: Trips deleted with integration | US-4 | Delete integration -> verify trips removed from storage |
| TE-7: p_deferrable index visible | US-5 | Publish to EMHASS -> verify index on trip cards |

### Test Implementation Order

1. Create failing tests that detect the bugs (tests should fail before fixes)
2. Implement fixes
3. Verify tests pass
4. Run full test suite to ensure no regressions

## Glossary

- **vehicle_id**: Unique identifier derived from vehicle name (lowercased, spaces to underscores)
- **p_deferrable**: EMHASS deferrable load index for flexible energy scheduling (0, 1, 2, ...)
- **TripManager**: Component managing trip CRUD operations and HA storage persistence
- **DataUpdateCoordinator**: HA component coordinating data updates with refresh throttling
- **calcular_energia_kwh()**: Utility function calculating energy as `km * consumption / 100`
- **async_unload_entry()**: HA lifecycle method called when integration is removed
- **Panel URL**: The URL path registered with Home Assistant for the custom panel (e.g., `ev-trip-planner-chispitas`)
- **Cascade Delete**: Automatic deletion of child records when parent is deleted

## Out of Scope

- Adding new trip types beyond recurring and punctual
- Modifying EMHASS adapter logic beyond index assignment
- Creating new sensor types
- Changing panel visual styling
- Adding user authentication or multi-user support
- Implementing trip history or analytics
- Syncing trips with external calendars
- Supporting multiple EMHASS instances per vehicle

## Dependencies

- Home Assistant Core >= 2024.x
- `homeassistant.helpers.storage.Store` for trip persistence
- `homeassistant.components.panel_custom` for panel registration
- `DataUpdateCoordinator` from `homeassistant.helpers.update_coordinator`
- `calcular_energia_kwh()` utility function in `utils.py`
- TripManager class with `async_save_trips()`, `async_delete_trip()`, `async_delete_all_trips()`
- EMHASS adapter with `_index_map` and `get_assigned_index()`

## Success Criteria

- [ ] US-1: Adding a vehicle creates exactly one panel with consistent URL casing
- [ ] US-2: Debug logs show refresh activity at most once per 5 seconds during normal operation
- [ ] US-3: Energy field displays calculated value and cannot be manually edited
- [ ] US-4: Deleting an integration removes all associated trips from HA storage
- [ ] US-5: Each trip card displays its p_deferrable index after EMHASS publish
- [ ] All unit tests pass (pytest)
- [ ] All E2E tests pass (Playwright)
- [ ] No regressions in existing functionality

## Unresolved Questions

- Q1: Should duplicate panel registration (case-variant) be rejected with an error, or silently deduplicated?
- Q2: Is 5 seconds the appropriate debounce window, or should it be configurable?
- Q3: Should the energy field show the calculated value before first EMHASS publish, or only after?
- Q4: Is there a requirement to preserve trips if the integration is re-installed, or always delete on uninstall?
- Q5: What happens if EMHASS publish is called multiple times - should indices be reassigned or preserved?

## Next Steps

1. Create unit tests for all 5 issues (tests should fail before implementation)
2. Create E2E tests for user-facing behaviors
3. Implement FR-1, FR-2: Remove duplicate panel registration, ensure case-insensitive deduplication
4. Implement FR-3, FR-4, FR-10: Add debouncing to DataUpdateCoordinator with throttled logging
5. Implement FR-5, FR-6: Make energy field readonly and use `calcular_energia_kwh()` as primary source
6. Implement FR-7: Add `async_delete_all_trips()` call in `async_unload_entry()`
7. Implement FR-8, FR-9: Persist `emhass_index` and display in trip card UI
8. Run full test suite and verify all tests pass
9. Update `.progress.md` with learnings from implementation

---

## Learnings

- Previous learnings...
- Issue 1 (Duplicate Panels): Panel registered twice - once in config_flow._async_create_entry() and again in __init__.async_setup_entry(). Both use same lowercased vehicle_id but HA treats URLs as case-sensitive, creating two panels.
- Issue 2 (Panel Flickering): DataUpdateCoordinator with update_interval=30s but services call async_request_refresh() on every trip operation. No debouncing.
- Issue 3 (Estimated Energy): kwh field is user-provided but should be calculated from km x consumption. calcular_energia_kwh() exists but not used as primary source.
- Issue 4 (Cascade Delete): async_unload_entry() does NOT delete trips from TripManager storage. Trips remain orphaned.
- Issue 5 (p_deferrable Index): EMHASS adapter assigns indices but index NOT persisted with trip data.
- panel_custom.py registers a static panel at "ev-trip-planner" URL - separate from per-vehicle dynamic panels
- vehicle_id generation: vehicle_name.lower().replace(" ", "_") in config_flow.py line 725
- TripManager uses HA Store API for persistence (not raw file I/O)
- Test-first approach: Create failing tests that detect the bugs, then implement fixes

## NEW: EMHASS Deferrable Load Integration (Extended Scope)

### Context from User Request

Each trip is a deferrable load. EMHASS returns planning data per trip with sensor IDs like `sensor.p_deferrable0` having attributes:
```yaml
device_class: power
unit_of_measurement: W
friendly_name: Deferrable Load 0
deferrables_schedule:
  - date: "2026-03-29T23:00:00+00:00"
    p_deferrable0: "0.0"
  - date: "2026-03-30T00:00:00+00:00"
    p_deferrable0: "0.0"
  ...
```

### US-6: Display p_deferrable Schedule on Trip Cards
**As a** vehicle owner
**I want** to see the p_deferrable charging schedule on each trip card
**So that** I can understand when EMHASS plans to charge before each trip

**Acceptance Criteria:**
- [ ] AC-6.1: Trip card displays `p_deferrable{N}` schedule as a graphical chart
- [ ] AC-6.2: Trip card shows the expected SOC at trip start and SOC at trip end
- [ ] AC-6.3: Schedule updates automatically when EMHASS returns new planning data
- [ ] AC-6.4: Warning displayed if insufficient charging window is detected

### US-7: EMHASS JSON Format Transformation
**As a** vehicle owner
**I want** the panel to show sensor IDs with the correct EMHASS format
**So that** I can copy them into my EMHASS configuration

**Acceptance Criteria:**
- [ ] AC-7.1: Panel displays sensor ID(s) for deferrable load profiles in EMHASS-compatible format
- [ ] AC-7.2: For each deferrable load: start time, end time, nominal power are shown
- [ ] AC-7.3: Sensor format follows EMHASS API requirements (`def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, etc.)
- [ ] AC-7.4: User can copy sensor ID with one click

### US-8: Automation Template for Charge Control
**As a** vehicle owner
**I want** an automation that controls vehicle charging based on EMHASS plan
**So that** charging starts/stops automatically according to the schedule

**Acceptance Criteria:**
- [ ] AC-8.1: Automation template created (per-vehicle or global) that reads `sensor.emhass_perfil_diferible_{vehicle_id}`
- [ ] AC-8.2: Automation starts charging when `p_deferrableN > 0` and car is home and plugged
- [ ] AC-8.3: Automation stops charging when `p_deferrableN == 0` or SOC target reached
- [ ] AC-8.4: Automation respects manual mode override (input_boolean)
- [ ] AC-8.5: Automation template is provided at `docs/borrador/cargasAplazables.yaml` pattern

### US-9: Improved Charging Window Calculation
**As a** vehicle owner
**I want** the system to calculate charging windows between trips
**So that** EMHASS knows when the car can charge

**Acceptance Criteria:**
- [ ] AC-9.1: Charging window for trip N starts 6 hours after trip N-1 start time
- [ ] AC-9.2: Charging window for trip N ends at trip N start time
- [ ] AC-9.3: If charging window is insufficient, system pre-schedules charging in previous window
- [ ] AC-9.4: Warning shown on trip if total required charge exceeds available windows
- [ ] AC-9.5: SOC sensor integration triggers recalculation when car is home

### US-10: SOC-Based Trip Planning
**As a** vehicle owner
**I want** the system to calculate required SOC for each trip
**So that** I know if I need external charging

**Acceptance Criteria:**
- [ ] AC-10.1: Each trip shows expected SOC at start (based on previous charging)
- [ ] AC-10.2: Each trip shows expected SOC at end (arrival SOC)
- [ ] AC-10.3: System warns if expected SOC at trip start < required SOC for the trip
- [ ] AC-10.4: `sensor.emhass_perfil_diferible_{vehicle_id}` recalculates when:
  - Trip is added, modified, or deleted
  - SOC sensor changes and car is home and plugged
- [ ] AC-10.5: Display "External charging needed" warning if insufficient windows

### EMHASS API Parameters Reference

From `docs/borrador/BorradorLegacyParametrosEMHASS`:

| Parameter | Type | Description |
|-----------|------|-------------|
| `def_total_hours` | Array[float] | Hours needed for each deferrable load |
| `P_deferrable_nom` | Array[float] | Nominal power in Watts |
| `def_start_timestep` | Array[int] | Start index (0 = ASAP) |
| `def_end_timestep` | Array[int] | End index (deadline hour) |
| `treat_deferrable_load_as_semi_cont` | Array[bool] | Can load be paused? |
| `set_deferrable_load_single_constant` | Array[bool] | Constant power? |
| `P_deferrable` | Array[Array] | 168-value power profile (7 days) |

### New Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-11 | Display p_deferrable schedule chart on trip card | High |
| FR-12 | Show SOC at start/end on trip card | High |
| FR-13 | Generate EMHASS-compatible sensor format | High |
| FR-14 | Display sensor IDs in panel for user copy | Medium |
| FR-15 | Create automation template for charge control | High |
| FR-16 | Calculate charging windows between trips | High |
| FR-17 | Pre-charge in previous window if insufficient | Medium |
| FR-18 | Warn if external charging needed | Medium |
| FR-19 | Integrate SOC sensor for recalculation trigger | High |

### Out of Scope (Extended)

- Implementing actual EMHASS API communication (only sensor generation)
- Hardware-specific charge controller integration
- Multi-vehicle coordination beyond separate deferrable indices
- Weather/price-based optimization
