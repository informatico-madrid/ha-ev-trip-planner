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
| `__init__.py` | 406-427, 802-853, 856-973 | Orphan detection and cleanup, panel unregistration |
| `panel.py` | 139-145 | Panel cleanup error handling |
| `panel.js` | 1008-1064 | Sensor filtering that causes cross-vehicle issue |

---

## Research Sources

- `.research-emhass-lifecycle.md` - EMHASS entity lifecycle deep dive
- `.research-panel-sensors.md` - Panel sensor aggregation analysis
- `.research-test-gap-analysis.md` - Test coverage gap analysis

---

# Additional Research: Panel Deletion Failure

## Executive Summary

The panel sidebar link persists after vehicle deletion because **panel cleanup is guarded by `if unload_ok:`** - if any earlier step in `async_unload_entry()` fails, the panel is NOT unregistered, leaving a stale sidebar link.

---

## Panel Deletion Mechanism

### Cleanup Call Chain

1. User deletes vehicle via UI → HA calls `hass.config_entries.async_remove_entry(entry.entry_id)`
2. HA internally calls `async_unload_entry()` first, then `async_remove_entry()`
3. `async_unload_entry()` at `__init__.py:802-853` performs cleanup in sequence:
   - Cascade deletes trips (line 820)
   - Calls EMHASS cleanup (line 830)
   - Unloads platforms (line 832) → sets `unload_ok`
   - **Removes panel** (line 842) → only if `unload_ok`

### Critical Issue: Panel Cleanup Guarded by `unload_ok`

```python
# __init__.py:832-848
unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

if unload_ok:
    try:
        await async_unregister_panel(hass, vehicle_id)
    except Exception as ex:  # pragma: no cover
        _LOGGER.warning(
            "Failed to unregister panel for vehicle %s: %s",
            vehicle_id,
            ex,
        )
```

**Bug**: If platform unload fails (any platform returns False), `unload_ok` is False and `async_unregister_panel()` is **never called**.

### Separate Cleanup Paths

EMHASS cleanup and panel cleanup are **independent try blocks** - an exception in EMHASS cleanup does NOT prevent panel cleanup:

```python
# __init__.py:825-830
if emhass_adapter:
    await emhass_adapter.async_cleanup_vehicle_indices()

# __init__.py:832 - separate block
unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

# __init__.py:840-848 - panel cleanup, only if unload_ok
if unload_ok:
    await async_unregister_panel(hass, vehicle_id)
```

### Panel Unregistration Error Handling

```python
# panel.py:139-145
except Exception as ex:  # pylint: disable=broad-except
    _LOGGER.error(
        "Failed to unregister panel for vehicle %s: %s",
        vehicle_id,
        ex,
    )
    return False
```

Exceptions are caught and logged as errors, but the calling code also catches them as warnings. **Silent failure path**: if panel unregistration fails, it returns False but the caller only logs a warning.

### Vehicle ID Derivation Mismatch Risk

Both `async_unload_entry()` and `async_remove_entry()` compute `vehicle_id` the same way:
```python
vehicle_id = entry.data.get("vehicle_name").lower().replace(" ", "_")
```

But if `entry.data` was modified after initial registration, the computed `vehicle_id` might not match the original panel URL path that was registered.

---

## Root Causes

| Issue | Root Cause |
|-------|------------|
| Panel persists after vehicle delete | Panel cleanup guarded by `if unload_ok:` - skipped if platform unload fails |
| No error visibility | Panel failures logged as warnings only, not errors |
| Silent failure | `async_unregister_panel()` catches all exceptions and returns False - caller ignores return value |

---

## Panel Deletion Recommendations

### High Priority
1. **Remove `if unload_ok:` guard for panel cleanup** - panel cleanup should always run regardless of platform unload status
2. **Make panel cleanup failure fatal** - if panel unregistration fails, the overall operation should fail or retry
3. **Verify vehicle_id matches original** - before calling unregister, verify `vehicle_id` matches the original registration

### Medium Priority
4. **Add logging for successful panel cleanup** - currently only failures are logged
5. **Track panel URL in entry.data** - store the original panel URL path to ensure exact match on cleanup

---

# Additional Research: Test Gap Analysis

## Executive Summary

Tests passed but failed to catch 5 production bugs related to EMHASS sensor lifecycle management. The root cause is that tests mock `hass.states` (state machine) but do not verify entity registry cleanup, and lack integration tests for full vehicle deletion lifecycle.

---

## Bug-to-Test Gap Mapping

| Bug | Root Cause | Test Gap |
|-----|------------|----------|
| 1. Sensors not deleted | `async_cleanup_vehicle_indices()` only calls `hass.states.async_remove()`, not entity registry | Tests mock `hass.states.async_remove` but never check `entity_registry.async_remove()` |
| 2. Cross-vehicle contamination | Panel pattern `sensor.ev_trip_planner` too broad | NO tests for panel sensor filtering by vehicle_id |
| 3. Charging power not reflected | `publish_deferrable_loads()` not called when entry.data changes | NO tests for config entry change triggering republish |
| 4. `power_profile_watts` not updating | `async_update()` may not properly call `async_schedule_update_ha_state()` | Tests mock the method but never verify it's called |
| 5. Panel persists after delete | Panel cleanup guarded by `if unload_ok:` | NO integration test for full vehicle deletion flow |

---

## Detailed Test Gaps

### Bug 1: Sensors Not Deleted (State + Entity Registry)

**Test gap in `tests/test_integration_uninstall.py:191-296`**
- `test_full_unload_cleans_all_emhass_sensors` only verifies `hass.states.async_remove` was called
- **Never checks if `entity_registry.async_remove()` was called**
- Mock `hass.states.async_remove` but does NOT mock `er.async_get().async_remove()`

### Bug 2: Cross-Vehicle Sensor Contamination

**Test gap: NO tests for panel sensor filtering**
- `tests/test_panel.py` only tests registration/unregistration, NOT sensor filtering
- No test verifies panel's `_getVehicleStates()` properly filters by vehicle_id

### Bug 3: Charging Power Changes Not Reflected

**Test gap in `tests/test_deferrable_load_sensors.py:141-169`**
- `test_power_profile_watts_uses_charging_power_kw` only tests update uses configured power
- **Does NOT test that changing config entry triggers re-publish**

### Bug 4: `power_profile_watts` Not Updating

**Test gap in `tests/test_deferrable_load_sensors.py:257-281`**
- `test_sensor_updates_attributes` mocks `async_schedule_update_ha_state` (line 72)
- **Never verifies this method is actually CALLED after `_cached_attrs` update**

### Bug 5: Panel Sidebar Link Persists

**Test gap in `tests/test_panel.py:125-140`**
- `test_unregister_panel_success` only tests direct call
- **No integration test for full vehicle deletion including sidebar cleanup**

---

## Mocking Issues That Hide Real Behavior

### Issue 1: `hass.states` Mocked but `entity_registry` Not

In `tests/test_integration_uninstall.py:203-207`, only `hass.states.async_remove` is mocked, NOT `entity_registry.async_remove()`. Bug #1 goes undetected because tests never check registry state.

### Issue 2: `async_schedule_update_ha_state` Mocked Away

In `tests/test_deferrable_load_sensors.py:72`, the method is mocked. Bug #4 goes undetected because the method that propagates attributes to HA state is mocked away.

### Issue 3: No Real Entity Registry Interaction

Tests use `mock_entity_registry` fixture but it's only used in config flow tests. EMHASS sensor tests do NOT use it. No test ever verifies `entity_registry.async_remove()` is called.

---

## Specific File:Line References

| File | Lines | Issue |
|------|-------|-------|
| `tests/test_deferrable_load_sensors.py` | 63-73 | `sensor` fixture mocks `async_schedule_update_ha_state` but doesn't test it gets called |
| `tests/test_deferrable_load_sensors.py` | 257-281 | `test_sensor_updates_attributes` doesn't verify schedule update is called |
| `tests/test_deferrable_load_sensors.py` | 141-169 | `test_power_profile_watts_uses_charging_power_kw` doesn't test config change triggers republish |
| `tests/test_integration_uninstall.py` | 191-296 | `test_full_unload_cleans_all_emhass_sensors` only checks `hass.states.async_remove`, never `entity_registry.async_remove` |
| `tests/test_panel.py` | 125-140 | `test_unregister_panel_success` doesn't test panel removal as part of full vehicle deletion |

---

## Test Improvement Recommendations

### Priority 1: Add Entity Registry Verification

After testing `hass.states.async_remove`, verify entity registry cleanup:
```python
from homeassistant.helpers import entity_registry as er
registry = er.async_get(mock_hass)
for entity_id in expected_removed:
    entry = registry.async_get(entity_id)
    assert entry is None, f"Entity {entity_id} should be removed from registry"
```

### Priority 2: Add Test for Config Change Triggering Republish

```python
async def test_charging_power_config_change_triggers_update(sensor, mock_hass):
    # Simulate config change (charging power updated)
    mock_entry = Mock(data={**entry.data, "charging_power_kw": 7.2})
    sensor.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
    
    # Trigger re-update and verify republish is called
```

### Priority 3: Add Integration Test for Full Vehicle Deletion Lifecycle

Test full deletion flow: async_setup_entry → create trips → verify sensors → async_unload_entry → verify all cleanup (state, registry, panel).

### Priority 4: Test Panel Sensor Filtering

Register two vehicles, verify panel for vehicle_1 only sees vehicle_1's sensors, not vehicle_2's.