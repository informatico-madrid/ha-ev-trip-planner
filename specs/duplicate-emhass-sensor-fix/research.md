---
spec: duplicate-emhass-sensor-fix
phase: research
created: 2026-04-04
---

# Research: Duplicate EMHASS Sensor Fix

## Executive Summary

Two bugs were investigated:

1. **Bug 1 - Duplicate Sensor After Integration Re-creation**: When user deleted integration "chispitas" and created "chispis", the old `chispitas` EMHASS sensor survives because state-based entities created via `hass.states.async_set()` are NOT cleaned up during `async_unload_entry()`. The sensor remains orphaned in HA's state machine.

2. **Bug 2 - Attributes Not Updating**: When trips or car SOC change, the sensor's `last_update` timestamp DOES update but `power_profile_watts` and `deferrables_schedule` do NOT. Root cause: `EmhassDeferrableLoadSensor.async_update()` sets `_cached_attrs` but does NOT call `async_schedule_update_ha_state()` to persist changes.

---

## Bug 1: Duplicate EMHASS Sensor After Integration Re-creation

### User Scenario

- Deleted integration "chispitas"
- Created integration "chispis"
- Two sensors appear:
  - `ev_trip_planner_chispitas_emhass_perfil_diferible_01kn2grt12chd6x52pn0d5ndtr` (SHOULD NOT EXIST)
  - `ev_trip_planner_chispis_emhass_perfil_diferible_01kncm2bw23n1faeye5kg8cdq9` (expected new sensor)

### Root Cause

**Two competing entity creation mechanisms:**

| Mechanism | How | Cleanup on Unload |
|-----------|-----|-------------------|
| `EmhassDeferrableLoadSensor` | Entity registry via `async_add_entities()` | Yes - removed via `async_unload_platforms()` |
| `hass.states.async_set()` direct | State machine bypass | **NO** - survives indefinitely |

**Step-by-step what happened:**

1. User CREATES "chispitas" integration
   - HA generates entry_id: `01kn2grt12chd6x52pn0d5ndtr`
   - `publish_deferrable_loads()` creates `sensor.emhass_perfil_diferible_01kn2grt12chd6x52pn0d5ndtr`

2. User DELETES "chispitas" integration
   - `async_unload_entry()` called
   - Deletes trips via `trip_manager.async_delete_all_trips()`
   - **DOES NOT call `async_cleanup_vehicle_indices()`**
   - `sensor.emhass_perfil_diferible_01kn2grt12chd6x52pn0d5ndtr` **SURVIVES**

3. User CREATES "chispis" integration
   - HA generates NEW entry_id: `01kncm2bw23n1faeye5kg8cdq9`
   - New sensor created with new entry_id

4. **Result:** Both sensors exist - old one is orphaned

### Key Code Paths

**`publish_deferrable_loads()` - emhass_adapter.py:509-520:**
```python
sensor_id = f"sensor.emhass_perfil_diferible_{self.entry_id}"
await self.hass.states.async_set(
    sensor_id,
    EMHASS_STATE_READY,
    {
        "power_profile_watts": power_profile,
        "deferrables_schedule": deferrables_schedule,
        ...
    },
)
```
Uses `self.entry_id` (HA config entry ID). Each re-creation gets a NEW entry_id.

**`async_cleanup_vehicle_indices()` - emhass_adapter.py:1105-1163:**
```python
# Sets to "idle" - does NOT remove from state machine
await self.hass.states.async_set(config_sensor_id, "idle", {})
await self.hass.states.async_set(sensor_id, "idle", {...})
```
Sets to "idle" instead of calling `async_remove()`. Entities remain.

**`async_unload_entry()` - __init__.py:775-819:**
```python
if trip_manager:
    await trip_manager.async_delete_all_trips()

unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
hass.data[DATA_RUNTIME].pop(namespace, None)
```
**DOES NOT call `emhass_adapter.async_cleanup_vehicle_indices()`**. State-based entities never cleaned.

### Why `chispitas` Sensor Appears in `chispis` Panel

The panel queries all `emhass_perfil_diferible` sensors. The orphaned `chispitas` sensor (with old entry_id `01kn2grt12chd6x52pn0d5ndtr`) still exists and appears alongside the new `chispis` sensor.

### Relationship Between `entry_id` and Sensor Names

| Component | ID Used | Changes on Re-creation? |
|-----------|---------|------------------------|
| HA Config Entry | `entry.entry_id` | YES - new random ID |
| Main EMHASS sensor | `sensor.emhass_perfil_diferible_{entry_id}` | YES - new sensor |
| Config sensors | `sensor.emhass_deferrable_load_config_{index}` | NO - uses index 0-49 |
| `EmhassDeferrableLoadSensor.unique_id` | `emhass_perfil_diferible_{entry_id}` | YES |

---

## Bug 2: Sensor Attributes Not Updating

### User Scenario

When trips or car SOC change:
- The sensor's `last_update` timestamp DOES change
- But internal attributes do NOT update:
  - `power_profile_watts`: hourly power values list
  - `deferrables_schedule`: detail of each hour and deferrable load

With a low car SOC, one would expect to see charging schedule showing power needed to reach target before trip starts.

### Root Cause

**Two conflicting update paths:**

**Path 1** (when trips change - direct state set):
```
async_save_trips() → _publish_deferrable_loads() → publish_deferrable_loads()
  → hass.states.async_set(sensor_id, state, attrs)
```
Sets `power_profile_watts` and `deferrables_schedule` directly in HA's state machine. `last_update` is NOT set here.

**Path 2** (HA's entity update cycle):
```
async_update() → generates new values → updates _cached_attrs → (MISSING: async_schedule_update_ha_state())
```
New values generated but NEVER reach HA's state machine.

### Why `last_update` Changes But Others Don't

1. `publish_deferrable_loads()` does NOT set `last_update` in its `hass.states.async_set()` call
2. Each time `async_update()` runs, it sets `self._cached_attrs["last_update"] = datetime.now().isoformat()`
3. The `extra_state_attributes` property returns `self._cached_attrs` directly
4. When HA reads attributes, it gets fresh `last_update` from `_cached_attrs`
5. But `power_profile_watts` and `deferrables_schedule` were set by Path 1's `hass.states.async_set()` and never updated by Path 2

### Missing Call in `async_update()`

**sensor.py:556-622** - `async_update()` is MISSING `self.async_schedule_update_ha_state()`:

```python
async def async_update(self) -> None:
    """Actualiza el estado del sensor."""
    try:
        power_profile = await self.trip_manager.async_generate_power_profile(...)
        schedule = await self.trip_manager.async_generate_deferrables_schedule(...)

        self._cached_attrs = {
            "power_profile_watts": power_profile,
            "deferrables_schedule": schedule,
            "last_update": datetime.now().isoformat(),
            ...
        }
        self._attr_native_value = EMHASS_STATE_READY

        # MISSING: self.async_schedule_update_ha_state()

    except Exception as err:
        # error handling...
```

### The Fix

Add `self.async_schedule_update_ha_state()` at end of the try block in `async_update()`:

```python
self.async_schedule_update_ha_state()
```

This ensures that when `async_update()` generates new values, they are properly persisted to HA's state machine.

---

## Bug Summary

| Bug | Location | Root Cause | Impact |
|-----|----------|------------|--------|
| 1. Orphaned sensors survive deletion | `emhass_adapter.publish_deferrable_loads()` | Creates state-based entities via `hass.states.async_set()` that bypass entity registry | Old sensors remain after integration deletion |
| 1. Cleanup doesn't remove entities | `async_cleanup_vehicle_indices()` | Sets to "idle" instead of calling `async_remove()` | Entities remain but marked idle |
| 1. Unload missing cleanup call | `__init__.py:async_unload_entry()` | Does not call `async_cleanup_vehicle_indices()` | State-based entities never cleaned |
| 2. Attributes don't persist | `sensor.py:async_update()` | Missing `async_schedule_update_ha_state()` call | `power_profile_watts` and `deferrables_schedule` remain stale |

---

## Feasibility Assessment

| Aspect | Bug 1 | Bug 2 |
|--------|-------|-------|
| Technical Viability | High | High |
| Effort Estimate | M | S |
| Risk Level | Medium | Low |
| Fix Complexity | Requires adding entity tracking and cleanup | Single method call addition |

---

## Recommendations for Requirements

### Bug 1 Fixes

1. **Track state-based entities in EMHASSAdapter**: Add a set to track all created state-based entities (main sensor + config sensors).

2. **Add `async_remove_all_deferrable_entities()` method**: Call `hass.states.async_remove()` for each tracked entity instead of setting to "idle".

3. **Call cleanup from `async_unload_entry()`**: Before unloading platforms, call the new cleanup method.

4. **Change `async_cleanup_vehicle_indices()` to remove**: Use `async_remove()` not `async_set(state, "idle")`.

5. **Consider single source of truth**: Remove `hass.states.async_set()` path for main sensor. Let `EmhassDeferrableLoadSensor` be the only entity managing EMHASS profile. `publish_deferrable_loads()` should trigger entity update, not bypass it.

### Bug 2 Fix

1. **Add `self.async_schedule_update_ha_state()`**: At end of try block in `async_update()` (after line ~605).

2. **Consider consolidating update paths**: Instead of two competing paths, have `publish_deferrable_loads()` call the entity's update method or set a flag to trigger update.

---

## Open Questions

- Should orphaned entities from previous versions be cleaned up during `async_setup_entry()`?
- Should `publish_deferrable_loads()` be refactored to update the entity through HA's entity system instead of direct state setting?
- Is there a reason `async_schedule_update_ha_state()` was intentionally omitted from `async_update()`?

---

## Sources

### Bug 1
- `emhass_adapter.py:509-520` - `publish_deferrable_loads()` creates state-based entities
- `emhass_adapter.py:1105-1163` - `async_cleanup_vehicle_indices()` sets to "idle" instead of removing
- `__init__.py:775-819` - `async_unload_entry()` does not clean state-based entities
- `sensor.py:624-627` - `async_will_remove_from_hass()` incomplete cleanup

### Bug 2
- `sensor.py:556-622` - `async_update()` missing `async_schedule_update_ha_state()`
- `sensor.py:551-554` - `extra_state_attributes` property
- `emhass_adapter.py:509-520` - `publish_deferrable_loads()` uses `hass.states.async_set()` directly
- `trip_manager.py:164-173` - `_publish_deferrable_loads()` calls `publish_deferrable_loads()`
- `trip_manager.py:341-381` - `async_save_trips()` calls `_publish_deferrable_loads()`
