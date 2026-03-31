# Requirements: EV Trip Planner Integration Fixes

## Goal

Fix 7 critical bugs in the EV Trip Planner Home Assistant integration: duplicate panels from case-sensitive URL handling, console flooding from aggressive refresh loops, broken cascade deletion of trips, orphaned sensors after vehicle removal, incorrect EMHASS power values, missing SOC display, and kWh manual input instead of auto-calculation.

## User Stories

### US-1: Prevent Duplicate Vehicle Panels
**As a** vehicle owner
**I want** only one panel to be created when I add a vehicle
**So that** I do not see duplicate entries in my Home Assistant sidebar

**Acceptance Criteria:**
- [ ] AC-1.1: **Given** a user adds a vehicle named "Chispitas", **when** the integration is set up, **then** exactly ONE panel is created (not two panels with URLs differing only in case like `/ev-trip-planner-chispitas` and `/ev-trip-planner-Chispitas`).
- [ ] AC-1.2: Panel URL uses normalized (lowercased) vehicle_id
- [ ] AC-1.3: No two panels exist with URLs differing only in case
- [ ] AC-1.4: Panel is registered in exactly one place (`__init__.py` OR `config_flow.py`, not both)
- [ ] AC-1.5: Vehicle_id is normalized to lowercase before panel registration in `__init__.py:471`

**Priority:** High

---

### US-2: Prevent Panel Refresh Flooding
**As a** vehicle owner
**I want** panel refreshes to occur at reasonable intervals
**So that** my console is not flooded with repetitive messages (1266+ occurrences)

**Acceptance Criteria:**
- [ ] AC-2.1: **When** a vehicle is recreated with the same name after deletion, **then** only one panel is created (not two with different cases like "Chispitas" and "chispitas"). Fixing US-1 eliminates duplicate panel loading that causes flooding.
- [ ] AC-2.2: WARNING logs for panel updates changed to DEBUG level
- [ ] AC-2.3: No single refresh event generates more than 1 log entry
- [ ] AC-2.4: Console shows < 10 messages per minute during normal operation
- [ ] AC-2.5: Unit test verifies log level is DEBUG, not WARNING

**Priority:** High

---

### US-3: Cascade Delete All Trips On Vehicle Removal
**As a** vehicle owner
**I want** all trips to be automatically deleted when I remove a vehicle
**So that** no orphaned trip data remains in Home Assistant storage

**Acceptance Criteria:**
- [ ] AC-3.1: **Given** a vehicle with trips exists in HA, **when** the user deletes the vehicle integration, **then** all trips for that vehicle are removed from TripManager storage (including recurring and punctual trips).
- [ ] AC-3.2: `async_delete_all_trips()` method exists in `trip_manager.py`
- [ ] AC-3.3: `__init__.py:739` calls `trip_manager.async_delete_all_trips()` successfully (method is implemented)
- [ ] AC-3.4: HA storage contains zero orphaned trip records after vehicle deletion
- [ ] AC-3.5: Unit test verifies `async_delete_all_trips()` is called during unload
- [ ] AC-3.6: Unit test verifies no trips remain for deleted vehicle_id

**Priority:** High

---

### US-4: Clean Up Old Sensors On Vehicle Removal
**As a** vehicle owner
**I want** old sensors like `sensor.ev_trip_planner_chispitas_emhass_perfil_diferible_01kn2grt...` to be removed when I delete a vehicle
**So that** stale sensors do not persist in my entity registry

**Acceptance Criteria:**
- [ ] AC-4.1: **Given** a vehicle with EMHASS sensors exists, **when** the vehicle is deleted, **then** all `EmhassDeferrableLoadSensor` entities are fully removed from HA (not orphaned like `sensor.ev_trip_planner_chispitas_emhass_perfil_diferible_01kn2grt...`).
- [ ] AC-4.2: All deferrable sensor entities for the vehicle are unregistered from HA
- [ ] AC-4.3: No sensor entities remain after vehicle removal (verified via HA entity registry)
- [ ] AC-4.4: Entity cleanup occurs in correct order during unload (before storage cleanup)
- [ ] AC-4.5: Unit test verifies entity removal during unload flow

**Priority:** High

---

### US-5: EMHASS Profile Displays Correct Power Values
**As a** vehicle owner
**I want** the EMHASS profile sensor to show correct power values (3600W)
**So that** I can verify the deferrable load is configured correctly

**Acceptance Criteria:**
- [ ] AC-5.1: **Given** a vehicle with configured battery capacity and SOC sensor, **when** the EMHASS schedule is generated, **then** the sensor displays 3600W (not all zeros).
- [ ] AC-5.2: Entry lookup in EMHASS adapter uses correct key (`entry_id`, not `vehicle_id`)
- [ ] AC-5.3: Return values from adapter methods are used (not discarded)
- [ ] AC-5.4: Unit test verifies `sensor.emhass_perfil_diferible_{vehicle_id}` returns non-zero power
- [ ] AC-5.5: Unit test verifies correct entry lookup logic

**Priority:** High

---

### US-6: SOC Display Using Configured Sensor
**As a** vehicle owner
**I want** the panel to display the State of Charge (SOC) from my configured sensor
**So that** I can monitor battery level in the trip planner dashboard

**Acceptance Criteria:**
- [ ] AC-6.1: **Given** a vehicle configured with a SOC sensor (e.g., `sensor.ovms_chispitas_metric_v_b_soc`), **when** the dashboard loads, **then** it displays the SOC value from that configured sensor (not a hardcoded `sensor.{vehicle_id}_soc`).
- [ ] AC-6.2: Dashboard uses the correct sensor name from vehicle configuration
- [ ] AC-6.3: SOC updates automatically when sensor value changes
- [ ] AC-6.4: Unit test verifies SOC is retrieved from configured sensor
- [ ] AC-6.5: Unit test verifies dashboard uses `soc_sensor` attribute, not hardcoded name

**Priority:** High

---

### US-7: kWh Auto-Calculation From Distance and Consumption
**As a** vehicle owner
**I want** the kWh field to be automatically calculated from distance and consumption
**So that** I see accurate energy requirements without manual calculation

**Acceptance Criteria:**
- [ ] AC-7.1: **Given** a trip with distance_km and vehicle consumption configured, **when** the trip is created or distance changes, **then** kWh is automatically calculated (read-only, user cannot manually edit).
- [ ] AC-7.2: kWh auto-calculated as `distance_km * vehicle_consumption_kwh_per_100km / 100`
- [ ] AC-7.3: kWh recalculates automatically when distance changes
- [ ] AC-7.4: Calculation uses vehicle's stored consumption value
- [ ] AC-7.5: Unit test verifies correct calculation for known distance and consumption
- [ ] AC-7.6: Unit test verifies kWh field is readonly in dashboard form

**Priority:** High

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Single Panel Registration | High | Panel registered once per vehicle in `async_setup_entry`, NOT in `_async_create_entry` |
| FR-2 | Case-Insensitive vehicle_id | High | `__init__.py:471` normalizes vehicle_id to lowercase before panel registration |
| FR-3 | Cascade Trip Deletion | High | `async_unload_entry()` calls `trip_manager.async_delete_all_trips(vehicle_id)` |
| FR-4 | Entity Cleanup On Unload | High | `EmhassDeferrableLoadSensor.async_will_remove_from_hass()` called for all entities |
| FR-5 | Correct EMHASS Entry Lookup | High | Adapter uses correct entry key, return values are assigned to variable and used |
| FR-6 | SOC From Configured Sensor | High | Dashboard reads `vehicle_config.soc_sensor`, not hardcoded sensor name |
| FR-7 | kWh ReadOnly Auto-Calculate | High | Dashboard form sets `readonly` on kWh field, value computed via `calcular_energia_kwh()` |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Panel Load Time | Time from sidebar click to panel visible | < 2 seconds |
| NFR-2 | Console Log Volume | Debug/Warning messages per minute during idle | < 10 msg/min |
| NFR-3 | Memory Usage | Additional memory for integration | < 30MB |

## Test Requirements

### Unit Tests (pytest)

| Test ID | Coverage | Location |
|---------|----------|----------|
| TU-1: Duplicate panel detection | FR-1, FR-2 | `tests/test_config_flow.py` |
| TU-2: Case-normalized vehicle_id | FR-2 | `tests/test___init__.py` |
| TU-3: Console log level DEBUG | AC-2.2 | `tests/test_coordinator.py` |
| TU-4: async_delete_all_trips exists and called | FR-3 | `tests/test_trip_manager.py` |
| TU-5: Entity cleanup on unload | FR-4 | `tests/test_emhass_sensor.py` |
| TU-6: EMHASS power values non-zero | FR-5 | `tests/test_emhass_adapter.py` |
| TU-7: SOC from configured sensor | FR-6 | `tests/test_dashboard.py` |
| TU-8: kWh readonly and calculated | FR-7 | `tests/test_dashboard.py` |

### Integration Tests (E2E Playwright)

| Test ID | User Story | Flow |
|---------|------------|------|
| TE-1: Single panel after vehicle add | US-1 | Config flow -> verify one panel in sidebar |
| TE-2: No console flooding | US-2 | Add vehicle -> verify < 10 msg/min in console |
| TE-3: Trips deleted with integration | US-3 | Delete integration -> verify trips removed |
| TE-4: No orphaned sensors | US-4 | Delete vehicle -> verify entity registry clean |
| TE-5: EMHASS sensor shows 3600W | US-5 | Configure EMHASS -> verify power value |
| TE-6: SOC visible in panel | US-6 | Configure SOC sensor -> verify display |
| TE-7: kWh auto-calculated | US-7 | Enter distance -> verify kWh calculated |

## Glossary

- **vehicle_id**: Unique identifier from vehicle name (lowercased, spaces to underscores)
- **Panel URL**: URL path registered with HA for custom panel (e.g., `ev-trip-planner-chispitas`)
- **SOC**: State of Charge - battery level percentage
- **EMHASS**: Energy Management for Home Assistant - handles deferrable load scheduling
- **Deferrable Load**: Flexible energy load that can be scheduled (e.g., vehicle charging)
- **p_deferrable**: Power value (Watts) for a deferrable load at a given timestep
- **TripManager**: Component managing trip CRUD operations and HA storage persistence
- **EmhassDeferrableLoadSensor**: HA sensor entity for EMHASS deferrable load profile
- **async_unload_entry()**: HA lifecycle method called when integration is removed
- **Cascade Delete**: Automatic deletion of child records (trips) when parent (vehicle) is deleted
- **calcular_energia_kwh()**: Utility function calculating energy as `km * consumption / 100`

## Out of Scope

- Adding new trip types beyond recurring and punctual
- Modifying EMHASS adapter logic beyond entry lookup fix
- Creating new sensor types beyond bug fixes
- Changing panel visual styling
- Adding user authentication or multi-user support
- Supporting multiple EMHASS instances per vehicle

## Dependencies

- Home Assistant Core >= 2024.x
- `homeassistant.helpers.storage.Store` for trip persistence
- `homeassistant.components.panel_custom` for panel registration
- `DataUpdateCoordinator` from `homeassistant.helpers.update_coordinator`
- TripManager class with `async_save_trips()`, `async_delete_trip()`, `async_delete_all_trips()`
- EMHASS adapter with deferrable load scheduling
- `calcular_energia_kwh()` utility function in `utils.py`

## Success Criteria

- [ ] US-1: Adding a vehicle creates exactly one panel with normalized URL
- [ ] US-2: Console shows < 10 messages per minute during normal operation
- [ ] US-3: Deleting an integration removes all associated trips
- [ ] US-4: No orphaned sensors remain after vehicle removal
- [ ] US-5: EMHASS profile sensor displays correct power values (3600W)
- [ ] US-6: SOC displayed from configured sensor in dashboard
- [ ] US-7: kWh field is read-only and auto-calculated
- [ ] All unit tests pass (pytest)
- [ ] All E2E tests pass (Playwright)
- [ ] No regressions in existing functionality

## Unresolved Questions

- Q1: Should duplicate panel registration (case-variant) be rejected with an error, or silently deduplicated?
- Q2: Is 5 seconds the appropriate debounce window, or should it be configurable?
- Q3: Should the energy field show the calculated value before first EMHASS publish, or only after?

## Next Steps

1. Create unit tests for all 7 bugs (tests should fail before implementation)
2. Create E2E tests for user-facing behaviors
3. Implement FR-1, FR-2: Remove duplicate panel registration, normalize vehicle_id in `__init__.py`
4. Implement FR-3: Add `async_delete_all_trips()` method to TripManager, call from `__init__.py`
5. Implement FR-4: Verify EmhassDeferrableLoadSensor cleanup on unload
6. Implement FR-5: Fix entry lookup in EMHASS adapter, use returned values
7. Implement FR-6: Use configured `soc_sensor` in dashboard
8. Implement FR-7: Make kWh field readonly and use `calcular_energia_kwh()`
9. Run full test suite and verify all tests pass
10. Update `.progress.md` with learnings from implementation