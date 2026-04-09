# Requirements: Fix EMHASS Sensor Attributes

## Goal

Arreglar el sensor EMHASS de perfil diferible que muestra atributos vacíos y crea dispositivos duplicados en Home Assistant, causado por dos bugs separados en `EmhassDeferrableLoadSensor`: `device_info` usa `entry_id` en lugar de `vehicle_id`, y el flujo de datos EMHASS → coordinator → sensor no pobla correctamente el cache.

---

## User Stories

### US-1: Single Device per Vehicle in Home Assistant UI

**As a** Home Assistant user
**I want** all sensors for my vehicle to appear under a single device
**So that** I can see all my EV Trip Planner entities grouped correctly in the UI

**Acceptance Criteria:**
- [ ] AC-1.1: `EmhassDeferrableLoadSensor.device_info` uses `vehicle_id` in `identifiers`, not `entry_id`
- [ ] AC-1.2: Only one device appears in HA UI per vehicle (e.g., "EV Trip Planner chispitas" with 8 entities)
- [ ] AC-1.3: No duplicate device with UUID/`entry_id` as device identifier
- [ ] AC-1.4: All vehicle sensors share the same `identifiers={(DOMAIN, vehicle_id)}` pattern

---

### US-2: EMHASS Sensor Attributes Populated with Real Values

**As a** Home Assistant user
**I want** the `sensor.emhass_perfil_diferible_*` to show actual power profile and schedule data
**So that** I can use the sensor in automations and dashboards for charging optimization

**Acceptance Criteria:**
- [ ] AC-2.1: `power_profile_watts` attribute contains array of 168 values (not `null`)
- [ ] AC-2.2: `deferrables_schedule` attribute contains schedule list with timestamps (not `null`)
- [ ] AC-2.3: `emhass_status` attribute contains state string ("ready", "active", "idle")
- [ ] AC-2.4: Values are populated from `EMHASSAdapter._cached_*` attributes via coordinator

---

### US-3: EMHASS Sensor Updates When SOC Changes

**As a** Home Assistant user
**I want** the EMHASS sensor to recalculate when my EV's SOC changes significantly
**So that** charging recommendations reflect my current battery level

**Acceptance Criteria:**
- [ ] AC-3.1: SOC change >=5% triggers `PresenceMonitor._async_handle_soc_change()`
- [ ] AC-3.2: SOC change propagates to `TripManager.async_generate_power_profile()`
- [ ] AC-3.3: `EMHASSAdapter.publish_deferrable_loads()` caches new profile
- [ ] AC-3.4: `coordinator.async_request_refresh()` propagates to sensor
- [ ] AC-3.5: Sensor `extra_state_attributes` reflect new values within 2 seconds

---

### US-4: EMHASS Sensor Updates When Trips Change

**As a** Home Assistant user
**I want** the EMHASS sensor to recalculate when I create, modify, or delete trips
**So that** charging schedule reflects my actual travel plans

**Acceptance Criteria:**
- [ ] AC-4.1: Creating a trip triggers `publish_deferrable_loads()` via service handler
- [ ] AC-4.2: Editing a trip triggers recalculation of power profile
- [ ] AC-4.3: Deleting a trip triggers recalculation of power profile
- [ ] AC-4.4: Sensor attributes update within 2 seconds of trip CRUD operation

---

### US-5: EMHASS Sensor Updates with Time (Hourly Rotation)

**As a** Home Assistant user
**I want** the power profile to rotate hourly so index 0 always represents the next full hour
**So that** my charging schedule stays synchronized with actual time

**Acceptance Criteria:**
- [ ] AC-5.1: `power_profile_watts[0]` represents the next full hour (e.g., at 9:30, index 0 = 10:00-11:00)
- [ ] AC-5.2: Profile rotates automatically on coordinator refresh (hourly or on trigger)
- [ ] AC-5.3: Time-based updates trigger via `ScheduleMonitor` or coordinator polling

---

### US-T1: Existing Unit Tests Must Pass

**As a** developer
**I want** existing unit tests to pass after fixes
**So that** we know the fixes don't break existing functionality

**Acceptance Criteria:**
- [ ] AC-T1.1: All 20 tests in `tests/test_deferrable_load_sensors.py` pass
- [ ] AC-T1.2: `test_sensor_device_info` updated to expect `vehicle_id` in identifiers (not `entry_id`)
- [ ] AC-T1.3: New test added verifying `device_info` uses consistent `vehicle_id` across all sensors
- [ ] AC-T1.4: Coverage for `EmhassDeferrableLoadSensor` remains at 100%

**Note**: Current `test_sensor_device_info` at line 287 expects `{(DOMAIN, "test_entry_id")}` which is the BUGGY behavior. This test must be updated to expect `{(DOMAIN, vehicle_id)}`.

---

### US-T2: E2E Test Validates EMHASS Sensor Updates Visible in UI

**As a** QA engineer
**I want** an E2E test that validates the EMHASS sensor updates are visible in the Home Assistant UI
**So that** we know the entire data flow works end-to-end

**Acceptance Criteria:**
- [ ] AC-T2.1: E2E test exists in `tests/e2e/emhass-sensor-updates.spec.ts`
- [ ] AC-T2.2: Test creates a trip and verifies `power_profile_watts` contains non-zero values
- [ ] AC-T2.3: Test simulates SOC change and verifies sensor attributes update
- [ ] AC-T2.4: Test verifies the EMHASS sensor state is visible in HA UI (developer tools > states)
- [ ] AC-T2.5: Test runs successfully with `make e2e`

**E2E Test Scenarios:**
1. Create trip → verify `power_profile_watts` has charging values at correct hours
2. Change SOC sensor state → verify `emhass_status` changes (e.g., "idle" → "ready")
3. Delete trip → verify `power_profile_watts` returns to all zeros
4. Verify device appears as single device in HA UI

---

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | `EmhassDeferrableLoadSensor.device_info` must use `vehicle_id` in identifiers | High | AC-1.1, AC-1.2, AC-T1.3 |
| FR-2 | EMHASS data flows from `EMHASSAdapter._cached_*` → `coordinator.data` → `sensor.attributes` | High | AC-2.1, AC-2.2, AC-2.3, AC-2.4 |
| FR-3 | `publish_deferrable_loads()` must cache values before calling `coordinator.async_request_refresh()` | High | AC-2.4 |
| FR-4 | SOC changes >=5% MUST trigger full EMHASS recalculation (currently broken - needs routing fix) | High | AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5 |
| FR-5 | Trip CRUD operations trigger EMHASS recalculation via service handlers | High | AC-4.1, AC-4.2, AC-4.3, AC-4.4 |
| FR-6 | Power profile rotates hourly to keep index 0 aligned with next full hour | Medium | AC-5.1, AC-5.2, AC-5.3 |
| FR-7 | Unit test for `device_info` updated to expect correct `vehicle_id` behavior | High | AC-T1.2, AC-T1.3 |
| FR-8 | E2E test validates EMHASS sensor updates visible in HA UI | High | AC-T2.1, AC-T2.2, AC-T2.3, AC-T2.4, AC-T2.5 |
| FR-9 | `TripPlannerCoordinator` must expose `vehicle_id` property OR `EmhassDeferrableLoadSensor` must receive `vehicle_id` as constructor parameter | High | AC-1.1, AC-1.3 |
| FR-10 | Fix method routing: `PresenceMonitor._async_handle_soc_change()` or `TripManager._publish_deferrable_loads()` must call the method that actually caches (`publish_deferrable_loads()` without async, not `async_publish_deferrable_loads()`) | High | AC-2.1, AC-2.2, AC-2.3, AC-2.4 |

---

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Sensor update latency | Time from trigger to HA state update | < 2 seconds |
| NFR-2 | Test coverage | Line coverage for affected modules | 100% |
| NFR-3 | E2E test reliability | Flaky test rate | 0% (must pass consistently) |
| NFR-4 | Performance | Coordinator refresh time | < 500ms for typical trip load |

---

## Glossary

| Term | Definition |
|------|------------|
| `vehicle_id` | User-configured vehicle identifier (e.g., "chispitas") - the friendly name chosen by the user |
| `entry_id` | Home Assistant-generated UUID for a config entry (e.g., "01234567-89ab-cdef-0123-456789abcdef") |
| `power_profile_watts` | Array of 168 float values representing charging power (watts) for each hour of next 7 days |
| `deferrables_schedule` | List of dicts with ISO timestamps and power values for EMHASS optimization |
| `emhass_status` | String state: "idle" (no charging needed), "ready" (charging needed), "active" (charging), "error" |
| `device_info` | HA entity property that groups entities under devices in the UI |
| `identifiers` | Tuple of `(DOMAIN, id)` that uniquely identifies a device in HA |

---

## Out of Scope

- Refactoring of EMHASS prediction algorithm or optimization logic
- Changes to trip CRUD operations beyond triggering EMHASS recalculation
- UI/UX improvements to the Lovelace dashboard
- Migration of existing orphaned devices (manual cleanup via HA UI)
- Changes to `TripPlannerSensor` or other non-EMHASS sensors
- Backwards compatibility with sensor naming from pre-v1.0.0

---

## Dependencies

- Home Assistant 2024.x+ (entity registry, device info APIs)
- `custom_components.ev_trip_planner.sensor.EmhassDeferrableLoadSensor`
- `custom_components.ev_trip_planner.emhass_adapter.EMHASSAdapter`
- `custom_components.ev_trip_planner.coordinator.TripPlannerCoordinator`
- `custom_components.ev_trip_planner.presence_monitor.PresenceMonitor`
- `custom_components.ev_trip_planner.trip_manager.TripManager`
- Existing unit tests in `tests/test_deferrable_load_sensors.py`
- E2E test framework (Playwright) in `tests/e2e/`

---

## Verification Contract

**Project type**: `fullstack` — Has both UI (Lovelace panel) and HTTP API (Home Assistant services/state machine)

**Entry points**:
- `sensor.py:EmhassDeferrableLoadSensor` — Sensor entity definition
- `emhass_adapter.py:publish_deferrable_loads()` — Data caching and coordinator trigger
- `coordinator.py:_async_update_data()` — Coordinator data population
- `presence_monitor.py:_async_handle_soc_change()` — SOC change trigger
- E2E: `tests/e2e/emhass-sensor-updates.spec.ts` — New E2E test file
- E2E: HA Developer Tools > States page (entity state inspection)

**Observable signals**:
- PASS:
  - HA UI shows single device per vehicle (8 entities under "EV Trip Planner {vehicle_id}")
  - `sensor.emhass_perfil_diferible_*` state is not `unknown` or `unavailable`
  - `power_profile_watts` attribute is array of 168 floats (not `null`)
  - `deferrables_schedule` attribute is list of dicts (not `null`)
  - `emhass_status` attribute is "ready", "active", or "idle" (not `null`)
  - Sensor updates within 2 seconds after trip CRUD or SOC change
  - E2E test passes: `npx playwright test emhass-sensor-updates.spec.ts`

- FAIL:
  - Two devices appear for same vehicle in HA UI
  - Device named with UUID/`entry_id` instead of `vehicle_id`
  - Sensor attributes show `null` values
  - Sensor stuck in `unknown` state after initial setup
  - Sensor doesn't update after creating a trip
  - E2E test times out waiting for sensor update

**Hard invariants**:
- Auth/session: Home Assistant user must be authenticated (E2E uses storageState)
- Permissions: User must have read access to entity states and sensor attributes
- Data integrity: `vehicle_id` must not be confused with `entry_id` in device identifiers
- Adjacent flows: Trip CRUD operations must continue to work; presence monitor must not crash

**Seed data**:
- At least one vehicle config entry with `vehicle_id` configured
- At least one trip (puntual or recurrente) to trigger charging calculation
- SOC sensor entity with state tracking enabled
- EMHASS adapter initialized with `charging_power_kw` > 0

**Dependency map**:
- `specs/emhass-sensor-entity-lifecycle` — Introduced coordinator-based architecture; this spec fixes data flow bug
- `specs/duplicate-emhass-sensor-fix` — Addressed device duplication but may not have fixed all cases
- `custom_components/ev_trip_planner/calculations.py` — Business logic for power profile (no changes needed)
- `custom_components/ev_trip_planner/trip_manager.py` — Trip data management (no changes needed)

**Escalate if**:
- `publish_deferrable_loads()` is never called (no trigger path found) - **CRITICAL: routing bug**
- The wrong method (`async_publish_deferrable_loads()` singular) is being called instead of `publish_deferrable_loads()` (plural without async)
- `coordinator.async_request_refresh()` doesn't propagate to sensor updates
- `device_info` change causes entity registry conflicts or orphaned entities
- E2E test cannot access HA developer tools or state page
- Timing issues cause flaky E2E tests (need to adjust waits/retries)

---

## Success Criteria

1. All sensors for a vehicle appear under ONE device in HA UI
2. EMHASS sensor attributes contain actual data (not `null`)
3. Sensor updates within 2 seconds of relevant triggers (SOC, trips, time)
4. All unit tests pass with 100% coverage
5. E2E test validates end-to-end flow visible in HA UI

---

## Next Steps

1. Review and approve requirements with user
2. Run design phase to create detailed technical design
3. Generate tasks.md from design
4. Implement fixes following TDD (RED → GREEN → REFACTOR)
5. Update `test_sensor_device_info` to expect correct `vehicle_id` behavior
6. Create `tests/e2e/emhass-sensor-updates.spec.ts` E2E test
7. Run full test suite to verify fixes
