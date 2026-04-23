# E2E Test UX-01/UX-02 Root Cause Analysis and Fix

## Problem Statement
E2E tests UX-01 and UX-02 were failing because `power_profile_watts.some(v => v > 0)` returned false (all zeros) even when trips were successfully created and power profile calculation showed `non_zero=1` or `non_zero=2`.

## Root Cause Analysis

### Investigation Steps

1. **SOC Configuration**: Initial SOC was 80% in E2E environment, causing zero energy calculations (battery had 48kWh but trip only needed 27kWh). Fixed by changing SOC from 80% to 20% in `tests/ha-manual/configuration.yaml`.

2. **Data Propagation Issue**: The coordinator's `_async_update_data` was showing `emhass_power_profile non_zero=0` even when `_calculate_power_profile_from_trips` produced `non_zero=1`.

3. **Race Condition in `trip_manager.py`**: The `publish_deferrable_loads()` method was calling `coordinator.async_refresh()` AFTER `async_publish_all_deferrable_loads()`. This caused a race condition:
   - `async_publish_all_deferrable_loads()` correctly computed the power profile and called `coordinator.async_set_data()` to update coordinator.data
   - BUT `coordinator.async_refresh()` then triggered `_async_update_data()` which read from `get_cached_optimization_results()` - this returned stale/empty data because the EMHASS adapter's cache hadn't been properly populated yet
   - The coordinator refresh OVERWROTE the fresh data with stale values

4. **Service Handlers Missing EMHASS Publish**: The `handle_trip_create()` service handler in `services.py` was only calling `coordinator.async_refresh_trips()` after trip creation, NOT `publish_deferrable_loads()` which actually computes and updates the power profile.

### Code Flow Before Fix

```
handle_trip_create()
  ├── async_add_recurring_trip() → stores trip in TripManager
  └── coordinator.async_refresh_trips() → calls _async_update_data()
                                          └─ reads from get_cached_optimization_results()
                                             └─ returns STALE/EMPTY data
```

The EMHASS adapter's `async_publish_all_deferrable_loads()` was NEVER called after trip creation, so the power profile was never computed!

## Fixes Applied

### Fix 1: services.py - handle_trip_create() (and other handlers)
Changed from `coordinator.async_refresh_trips()` to `mgr.publish_deferrable_loads()`:

```python
# BEFORE (services.py lines 125-129):
coordinator = _get_coordinator(hass, vehicle_id)
if coordinator:
    _LOGGER.debug("Refrescando trips para vehículo: %s", vehicle_id)
    await coordinator.async_refresh_trips()

# AFTER:
coordinator = _get_coordinator(hass, vehicle_id)
if coordinator:
    _LOGGER.debug("Publishing deferrable loads for vehicle: %s", vehicle_id)
    try:
        await mgr.publish_deferrable_loads()  # Computes power profile AND updates coordinator.data
    except Exception as err:
        _LOGGER.warning(
            "Failed to publish deferrable loads for vehicle %s: %s",
            vehicle_id, err,
        )
```

This fix was applied to ALL service handlers:
- `handle_trip_create()`
- `handle_trip_update()`
- `handle_edit_trip()`
- `handle_delete_trip()`
- `handle_pause_recurring()`
- `handle_resume_recurring()`
- `handle_complete_punctual()`
- `handle_cancel_punctual()`

### Fix 2: trip_manager.py - publish_deferrable_loads()
Removed the call to `coordinator.async_refresh()`:

```python
# BEFORE (lines 279-338):
# 60+ lines of coordinator lookup and async_refresh() call

# AFTER:
# CRITICAL FIX: Do NOT call coordinator.async_refresh() here!
# async_publish_all_deferrable_loads() already updates coordinator.data directly
# via coordinator.async_set_data(). Calling async_refresh() would trigger
# _async_update_data() which reads from get_cached_optimization_results() and
# OVERWRITES the fresh data with stale values.
# Sensors update automatically when coordinator.data changes via async_set_data().
```

## Correct Code Flow After Fix

```
handle_trip_create()
  ├── async_add_recurring_trip() → stores trip in TripManager
  └── mgr.publish_deferrable_loads() → 
      ├── async_publish_all_deferrable_loads(trips)
      │   ├── _calculate_power_profile_from_trips() → produces non_zero power profile
      │   ├── _cached_power_profile = power_profile  → stores in EMHASS adapter cache
      │   └── coordinator.async_set_data({emhass_power_profile: [...]}) → updates coordinator.data
      └── (NO coordinator.async_refresh() - prevents race condition)
```

## Verification

The logs now show correct data propagation:

```
2026-04-22 13:04:02.514 WARNING E2E-DEBUG emhass_adapter: _calculate_power_profile_from_trips END - power_profile_length=168, non_zero=1
2026-04-22 13:04:10.451 WARNING E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: emhass_power_profile length=168, non_zero=2
2026-04-22 13:04:40.084 WARNING E2E-DEBUG EMHASS-SENSOR-CACHE-HUNT: emhass_power_profile length=168, non_zero=2
```

The power profile now correctly shows `non_zero=2` (multiple trips with non-zero power values).

## Files Modified

1. `custom_components/ev_trip_planner/services.py`
   - All service handlers now call `mgr.publish_deferrable_loads()` instead of `coordinator.async_refresh_trips()`

2. `custom_components/ev_trip_planner/trip_manager.py`
   - Removed `coordinator.async_refresh()` call in `publish_deferrable_loads()`
   - Added comment explaining why refresh is not needed

3. `tests/ha-manual/configuration.yaml`
   - Changed SOC from 80% to 20% for E2E testing (ensures energy calculations are needed)

## Key Insights

1. **async_set_data() vs async_refresh()**: `coordinator.async_set_data()` directly updates `coordinator.data` and notifies entities. `coordinator.async_refresh()` triggers `_async_update_data()` which reads from sources and can overwrite fresh data with stale values.

2. **EMHASS Publish is Required**: Simply storing a trip is NOT enough. `publish_deferrable_loads()` must be called to:
   - Calculate the power profile from trips
   - Store results in EMHASS adapter cache
   - Update coordinator.data with fresh values

3. **No Refresh After Direct Update**: When using `async_set_data()`, do NOT call `async_refresh()` afterward as it will overwrite the fresh data with stale data from `_async_update_data()`.
