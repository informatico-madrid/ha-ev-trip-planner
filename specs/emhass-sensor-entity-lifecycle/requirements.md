# Requirements: EMHASS Sensor Entity Lifecycle Fix

## Goal

Fix the EMHASS sensor entity lifecycle issues where sensors are not properly deleted, show on wrong vehicles' panels, and charging power changes are not reflected in sensor attributes.

---

## User Stories

### US-1: Proper Entity Cleanup on Vehicle Deletion

**As a** Home Assistant user  
**I want** all EMHASS sensors to be deleted when I delete a vehicle  
**So that** no orphaned sensors remain in the system

**Acceptance Criteria:**

- [ ] When a vehicle config entry is deleted, all `sensor.emhass_perfil_diferible_{entry_id}` entities are removed from both state machine and entity registry
- [ ] `async_cleanup_vehicle_indices()` removes both state entities (via `hass.states.async_remove()`) AND registry entries (via `entity_registry.async_remove()`)
- [ ] No errors logged during vehicle deletion
- [ ] No stale sensors persist after vehicle removal

---

### US-2: Vehicle-Specific Sensor Display

**As a** Home Assistant user  
**I want** each vehicle panel to show only sensors belonging to that specific vehicle  
**So that** I can see accurate, relevant information without confusion

**Acceptance Criteria:**

- [ ] Panel sensor filtering uses `sensor.emhass_perfil_diferible_{current_entry_id}` pattern (not generic `sensor.ev_trip_planner`)
- [ ] Panel displays sensors with matching `entry_id` attribute for the current vehicle
- [ ] No cross-vehicle sensor contamination (vehicle A panel doesn't show vehicle B's sensors)
- [ ] Sensor filtering works correctly after vehicle rename or reconfiguration

---

### US-3: Charging Power Updates Reflect in Sensor

**As a** Home Assistant user  
**I want** changes to charging power configuration to immediately reflect in EMHASS sensor attributes  
**So that** my sensor data accurately reflects current system configuration

**Acceptance Criteria:**

- [ ] When `charging_power_kw` is updated via config flow, `publish_deferrable_loads()` is re-called with new power value
- [ ] `power_profile_watts` attribute updates to reflect new charging power (kW × 1000 = watts)
- [ ] Attribute update happens immediately, not only on trip changes
- [ ] No manual restart required after config change

---

### US-4: power_profile_watts Attribute Updates Automatically

**As a** Home Assistant user  
**I want** the `power_profile_watts` sensor attribute to update automatically when vehicle parameters change  
**So that** automation and dashboards show current values without manual refresh

**Acceptance Criteria:**

- [ ] `EmhassDeferrableLoadSensor.async_update()` calls `async_schedule_update_ha_state()` after updating `_cached_attrs`
- [ ] Attribute changes propagate to Home Assistant state machine immediately
- [ ] Dashboard cards and automations see updated `power_profile_watts` value
- [ ] No state synchronization issues between state-machine and registry entities

---

### US-5: Panel Cleanup on Vehicle Deletion

**As a** Home Assistant user  
**I want** vehicle panel sidebar links to be removed when I delete a vehicle  
**So that** I don't see stale navigation links that lead to errors

**Acceptance Criteria:**

- [ ] Panel unregistration happens regardless of platform unload status (remove `if unload_ok:` guard)
- [ ] `async_unregister_panel()` is called in `async_unload_entry()` for all vehicle deletions
- [ ] No TypeError or navigation errors when accessing deleted vehicle panel
- [ ] Sidebar link removed immediately after vehicle deletion

---

## Functional Requirements

### FR-1: Entity Registry Cleanup Integration

**FR-1.1** `async_cleanup_vehicle_indices()` must call `entity_registry.async_remove()` for each `EmhassDeferrableLoadSensor` entity

- Implement cleanup loop that iterates through tracked entity registry entries
- Call `entity_registry.async_remove(entity_id)` for each entry
- Handle cases where entry already removed gracefully

**FR-1.2** State-only sensors must include `entry_id` attribute for orphan detection

- `publish_deferrable_loads()` must set `state.attributes["entry_id"]` to current `self.entry_id`
- Orphan detection in `__init__.py` must check `entry_id` attribute
- Cleanup logic must remove both state and registry entities for matching `entry_id`

---

### FR-2: Tightened Panel Sensor Patterns

**FR-2.1** Panel sensor filtering must use exact `entry_id` pattern

- Replace `sensor.ev_trip_planner` pattern with `sensor.emhass_perfil_diferible_{current_entry_id}`
- Filter by `entry_id` attribute match, not just pattern match
- Validate sensor has matching `entry_id` attribute before including in panel list

**FR-2.2** Panel must detect and handle orphaned sensors

- If sensor exists but `entry_id` doesn't match current vehicle, mark as orphan
- Orphan sensors should not appear in panel display
- Log warning when orphaned sensors detected

---

### FR-3: Reactive Attribute Updates

**FR-3.1** Config entry updates must trigger sensor republish

- Subscribe to config entry update events in `EmhASSAdapter`
- When `charging_power_kw` changes, call `publish_deferrable_loads()` with new power value
- Update all deferrable load sensor attributes immediately

**FR-3.2** Sensor async_update must schedule state write

- `EmhassDeferrableLoadSensor.async_update()` must call `async_schedule_update_ha_state()` after `_cached_attrs` update
- Ensure attribute propagation to Home Assistant state machine
- No mocked behavior in production code

---

### FR-4: Panel Cleanup on Vehicle Deletion

**FR-4.1** Remove `if unload_ok:` guard for panel cleanup

- Panel unregistration must always execute, regardless of platform unload status
- Move `async_unregister_panel()` call outside conditional block
- Ensure cleanup happens in all vehicle deletion paths

**FR-4.2** Add success logging for panel cleanup

- Log successful panel unregistration (not just failures)
- Include vehicle_id and timestamp in log message
- Enable troubleshooting of panel lifecycle issues

---

## Non-Functional Requirements

### NFR-1: Performance

- Entity registry cleanup must complete within 5 seconds for vehicles with up to 10 deferrable loads
- Panel sensor filtering must not cause visible UI lag (>100ms)
- Attribute updates must propagate within 1 second of trigger

### NFR-2: Reliability

- No sensor or panel cleanup operations should fail silently
- All cleanup operations must be idempotent (safe to run multiple times)
- System must recover gracefully from partial cleanup failures

### NFR-3: Maintainability

- Entity cleanup logic must be well-documented with clear comments
- Separation between state-only and registry entity handling must be explicit
- Code must follow Home Assistant integration best practices

### NFR-4: Debuggability

- Orphaned sensor detection must log warnings with full entity details
- Panel sensor filtering must include debug logging when patterns match unexpectedly
- Config change propagation must be traceable in logs

---

## Glossary

| Term | Definition |
|------|------------|
| `entry_id` | Home Assistant-generated unique identifier for a config entry (UUID format) |
| `async_cleanup_vehicle_indices()` | Method that removes EMHASS sensor state for a specific vehicle |
| `publish_deferrable_loads()` | Method that creates/updates EMHASS deferrable load sensor state |
| `EmhassDeferrableLoadSensor` | Home Assistant sensor entity registered via platform setup |
| state-only sensor | Entity created via `hass.states.async_set()` (not in entity registry) |
| registry entity | Entity created via `SensorEntity` subclass (in entity registry) |
| orphaned sensor | Sensor with stale `entry_id` that no longer belongs to current vehicle |

---

## Out of Scope

- Refactoring of existing trip management logic
- Changes to EMHASS API integration or prediction logic
- UI/UX improvements beyond sensor filtering correctness
- Backwards compatibility with pre-v1.0.0 sensor naming
- Migration of existing orphaned sensors (manual cleanup via HA UI)

---

## Dependencies

- Home Assistant 2024.x+ (entity registry API)
- Home Assistant panel registration API (`async_register_panel`, `async_unregister_panel`)
- Config entry update events (`config_entries.async_update_entry`)
- Entity registry cleanup API (`entity_registry.async_remove()`)

---

## Technical Constraints

1. **Dual entity paths**: Must handle both state-only sensors (created by `publish_deferrable_loads()`) AND registry sensors (created by `EmhassDeferrableLoadSensor` platform setup)

2. **Entry ID attribution**: State-only sensors must include `entry_id` attribute to enable orphan detection

3. **Panel filtering**: Panel must filter by exact `entry_id` match, not generic patterns

4. **Reactive updates**: Config entry changes must trigger sensor republish without manual intervention

5. **Cleanup coordination**: Entity registry cleanup must happen in parallel with state cleanup during vehicle deletion
