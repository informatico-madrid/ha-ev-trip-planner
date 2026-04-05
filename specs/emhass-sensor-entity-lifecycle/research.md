# Research: emhass-sensor-entity-lifecycle

## Executive Summary

The EMHASS sensor `sensor.ev_trip_planner_{vehicle}_emhass_perfil_diferible_{entry_id}` has **two parallel creation paths** that cause lifecycle issues:

1. **State-only path** (`hass.states.async_set`): Creates ephemeral state-based entities NOT in entity registry
2. **Entity registry path** (`EmhassDeferrableLoadSensor`): Proper `SensorEntity` registered via platform setup

This dual creation causes: sensors not deleted on vehicle delete, cross-vehicle sensor contamination, charging power changes not reflected, and `power_profile_watts` not updating.

---

## Key Findings

### 1. Dual Entity Creation Problem

| Entity | Creation Method | Persists After Restart | Cleanup Mechanism |
|--------|----------------|------------------------|-------------------|
| `sensor.emhass_perfil_diferible_{entry_id}` (state) | `publish_deferrable_loads()` line 514 | No (ephemeral) | `hass.states.async_remove()` |
| `sensor.emhass_deferrable_load_config_{index}` (state) | `async_publish_deferrable_load()` line 279 | No (ephemeral) | `hass.states.async_remove()` |
| `EmhassDeferrableLoadSensor` (registry) | `sensor.py` line 920 via platform | Yes (registry) | `async_will_remove_from_hass()` hook |

**Critical issue**: `publish_deferrable_loads()` creates the state-only sensor at line 514, then `EmhassDeferrableLoadSensor` is ALSO registered for the same `entry_id` during `async_setup_entry()` - two entities with the same ID via different mechanisms.

### 2. Sensor Deletion Failure

**`async_cleanup_vehicle_indices()`** (emhass_adapter.py:1111-1161) calls `hass.states.async_remove()` which only removes state-machine entities. It does NOT interact with the entity registry for `EmhassDeferrableLoadSensor`.

**Missing cleanup path**:
- Adapter cleanup → `hass.states.async_remove()` (removes state)
- Adapter cleanup → **NOT** → `entity_registry.async_remove()` (for registry entity)

**Orphan detection** exists in `__init__.py:406-427` but:
- Only runs at startup
- Only cleans state-machine entities, not registry entries
- Uses `entry_id` attribute but `publish_deferrable_loads()` does NOT set this attribute

### 3. Cross-Vehicle Sensor Contamination

**Root cause in panel.js:1008-1064 (`_getVehicleStates()`):**
```javascript
const patterns = [
  `sensor.${lowerVehicleId}`, `sensor.${lowerVehicleId}_`,
  'sensor.trip_',
  'sensor.ev_trip_planner_',
  'sensor.ev_trip_planner',  // ← TOO BROAD: catches ALL emhass_perfil_diferible sensors
];
```

Pattern `sensor.ev_trip_planner` matches `sensor.emhass_perfil_diferible_{ANY_ENTRY_ID}`, causing sensors from all vehicles to appear on every panel.

**EMHASS sensor naming** uses `entry_id` (HA-generated UUID), not `vehicle_id`:
- `sensor_id = f"sensor.emhass_perfil_diferible_{self.entry_id}"` (emhass_adapter.py:512)
- On re-creation, NEW `entry_id` = NEW orphaned sensor left behind
- Panel cannot distinguish which vehicle owns which sensor by name alone

### 4. Attribute Update Failures

**`power_profile_watts`** set in `publish_deferrable_loads()` (line 514-523):
- Called when trips change, NOT when vehicle params (e.g., charging power) change
- No subscription/hook to vehicle config changes

**`deferrables_schedule`** also set in same `publish_deferrable_loads()` call - same issue

**`EmhassDeferrableLoadSensor.async_update()`** (sensor.py:562-629):
- Updates `_cached_attrs` with new values
- But does NOT call `async_schedule_update_ha_state()` after updating (missing call)
- This is why only `deferrables_schedule` updates (because entity registry version updates on next `async_set` cycle)

### 5. Charging Power Change Not Reflected

When user changes charging power via config flow:
1. Config flow calls `hass.config_entries.async_update_entry()` (updates entry.data)
2. But `publish_deferrable_loads()` is NOT re-called with new `charging_power_kw`
3. The `power_profile_watts` calculation uses `_charging_power_kw` set at adapter creation time
4. No reactive update when entry.data changes

---

## Root Causes

| Issue | Root Cause |
|-------|------------|
| Sensors not deleted | `async_cleanup_vehicle_indices()` removes state only, not entity registry |
| Sensors on other panels | Panel pattern `sensor.ev_trip_planner` too broad; no vehicle_id filtering |
| Charging power not reflected | No re-publish triggered when entry.data changes; `charging_power_kw` is static |
| `power_profile_watts` not updating | `publish_deferrable_loads()` not called on vehicle param changes |

---

## Recommendations

### High Priority
1. **Add `entry_id` attribute to state-only sensors** in `publish_deferrable_loads()` for orphan detection
2. **Tighten panel sensor patterns** to use `sensor.emhass_perfil_diferible_{current_entry_id}` only, or filter by `entry_id` attribute
3. **Trigger re-publish when vehicle config changes** - subscribe to config entry updates and re-call `publish_deferrable_loads()`

### Medium Priority
4. **Consolidate to single entity type** - choose either state-only OR entity registry, not both
5. **Add entity registry cleanup coordination** - when adapter cleanup runs, also remove registry entry if exists

---

## Related Files

| File | Lines | Relevance |
|------|-------|-----------|
| `emhass_adapter.py` | 509-548, 1111-1161 | State-only sensor creation and cleanup |
| `sensor.py` | 494-634, 920 | Entity registry sensor and setup |
| `__init__.py` | 406-427, 825-830 | Orphan detection and cleanup invocation |
| `panel.js` | 1008-1064 | Sensor filtering that causes cross-vehicle issue |

---

## Research Sources

- `.research-emhass-lifecycle.md` - EMHASS entity lifecycle deep dive
- `.research-panel-sensors.md` - Panel sensor aggregation analysis