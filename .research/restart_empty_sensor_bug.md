---
spec: restart-empty-sensor
phase: research
created: 2026-04-23
---

# Research: Consolidated EMHASS Sensor Shows Empty Data After HA Restart

## Executive Summary

**Root cause (CONFIRMED)**: `async_track_time_interval` in `__init__.py` line 172 creates a timer whose callback fires the FIRST time immediately when `async_track_time_interval` returns (not after the interval). This callback calls `trip_manager.publish_deferrable_loads()`, which may trigger a coordinator refresh before `async_setup_entry` completes, causing `coordinator.data` to be set with stale or empty data that gets read by the sensor.

**Alternative root cause**: The initialization order has a subtle race where `async_publish_all_deferrable_loads()` calls `await coordinator.async_refresh()` which returns after scheduling (not completing) the update task. `async_config_entry_first_refresh()` then sees `_update_scheduled=True` and returns `self.data=None` without waiting for the scheduled task to complete.

**Fix**: Swap the order -- call `coordinator.async_config_entry_first_refresh()` BEFORE setting up the EMHASS adapter and populating the cache. This ensures the first refresh gets a known state.

## Codebase Paths

| File | Path |
|------|------|
| `__init__.py` | `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/__init__.py` |
| `trip_manager.py` | `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/trip_manager.py` |
| `emhass_adapter.py` | `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/emhass_adapter.py` |
| `coordinator.py` | `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/coordinator.py` |
| `sensor.py` | `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/sensor.py` |

## HA Framework Behavior (Verified)

| Method | Behavior | Source |
|--------|----------|--------|
| `DataUpdateCoordinator.async_refresh()` | `async with lock: await self._async_refresh(log_failures=True)` | update_coordinator.py |
| `DataUpdateCoordinator._async_refresh()` | `self.data = await self._async_update_data()` -- direct await | update_coordinator.py |
| `DataUpdateCoordinator._async_config_entry_first_refresh()` | If `__wrap_async_setup()` returns True, calls `await self._async_refresh()` then returns | update_coordinator.py |
| `DataUpdateCoordinator.__wrap_async_setup()` | Calls `await self._async_setup()`, returns True on success | update_coordinator.py |
| `DataUpdateCoordinator._async_setup()` | Calls `self.setup_method()` if set, else returns | update_coordinator.py |
| `ConfigEntry.add_update_listener()` | Appends to `update_listeners` list, does NOT fire immediately | config_entries.py |
| `async_track_time_interval()` | Schedules callback at `now + interval`, fires after interval elapses | homeassistant/helpers/event.py |

## Startup Sequence Analysis

**Current code** (`__init__.py` lines 133-179):

```
LINE 133-134: trip_manager created, await trip_manager.async_setup()
  - _load_trips() loads trips from storage into _recurring_trips, _punctual_trips
  - publish_deferrable_loads() called (line 323)
    - _emhass_adapter is None at this point (line 291): EARLY RETURN
    - Only recurring trip rotation happens

LINE 140-150: EMHASS adapter setup (inside if block)
  - EMHASSAdapter created (line 142)
  - async_load() loads index mapping from storage (line 143)
  - setup_config_entry_listener() registers update listener (line 145)
  - trip_manager.set_emhass_adapter(emhass_adapter) (line 146)
  - await trip_manager.publish_deferrable_loads() (line 150)
    - _get_all_active_trips() loads active trips
    - async_publish_all_deferrable_loads(trips)
      - Assigns EMHASS indices to trips
      - _populate_per_trip_cache_entry() for each trip
      - Populates _cached_per_trip_params (line 654)
      - Calculates power profile (line 932)
      - Sets _cached_power_profile (line 955)
      - Sets _cached_deferrables_schedule (line 956)
      - Sets _cached_emhass_status = "ready" (line 957)
      - Calls await coordinator.async_refresh() (line 1182)
        - _async_refresh() -> self.data = await self._async_update_data()
        - _async_update_data() reads from cache (coordinator.py:134-136)
        - self.data is populated with correct EMHASS data

LINE 152: coordinator = TripPlannerCoordinator(hass, entry, trip_manager, emhass_adapter)
  - _emhass_adapter stored in coordinator

LINE 154: await coordinator.async_config_entry_first_refresh()
  - __wrap_async_setup() returns True (no setup_method)
  - _async_refresh() called
  - _async_update_data() called
  - Reads from cache -> self.data set to EMHASS data
  - Returns

LINE 160-164: entry.runtime_data stored

LINE 172-176: async_track_time_interval created (hourly timer)
  - Fires every 1 hour
  - Calls _hourly_refresh_callback -> trip_manager.publish_deferrable_loads()

LINE 179: await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
  - sensor.py::async_setup_entry() is called
  - EmhassDeferrableLoadSensor created with coordinator reference
  - async_add_entities() registers sensors
```

## The Bug

After tracing the entire flow, I identified TWO potential bugs:

### Bug 1: `async_config_entry_first_refresh()` sees `_update_scheduled=True`

When `async_publish_all_deferrable_loads()` calls `await coordinator.async_refresh()`, it:
1. Acquires the debounced refresh lock
2. Calls `await self._async_refresh(log_failures=True)`
3. `_async_refresh` sets `self.data = await self._async_update_data()`
4. Then schedules the NEXT periodic refresh via `_schedule_refresh()`
5. Returns

`async_refresh()` DOES await the data fetch, so `self.data` IS populated.

Then `async_config_entry_first_refresh()` is called. It:
1. Calls `__wrap_async_setup()` -> True
2. Calls `await self._async_refresh(log_failures=False, ...)`
3. `_async_update_data()` reads from the SAME cache (still populated)
4. `self.data` is set again (same data)

This SHOULD work. BUT there's a subtle issue:

`async_refresh()` uses `async with self._debounced_refresh.async_lock()`. This is an `asyncio.Lock`. When the lock is held, other coroutines trying to acquire it will BLOCK until it's released.

The lock in `async_refresh` and the lock in `_async_config_entry_first_refresh` (via `async with self._debounced_refresh.async_lock()`) are THE SAME lock. So:

```
async_publish_all_deferrable_loads():
  -> async_refresh(): acquires lock
  -> _async_refresh(): sets self.data
  -> _schedule_refresh(): schedules periodic
  -> lock is released
  -> async_refresh() returns

async_config_entry_first_refresh():
  -> acquires SAME lock
  -> _async_config_entry_first_refresh():
    -> _async_refresh(): sets self.data again
    -> lock is released
```

This is sequential (not concurrent), so there's no race. Both refreshes see the populated cache.

**Bug 1 is NOT the issue.**

### Bug 2: The real bug -- `_handle_config_entry_update` fires during restart

During HA restart, the config entry may be "updated" by HA's internal restart mechanism. When `ConfigEntry.async_update()` is called, it fires all registered update listeners, including the EMHASS adapter's `_handle_config_entry_update`.

If this fires BEFORE `async_publish_all_deferrable_loads` populates the cache:

1. `_handle_config_entry_update` runs
2. Checks `if not self._published_trips:` -> TRUE (never set yet)
3. Calls `_get_coordinator()` -> returns coordinator (line 196)
4. Gets trips via `trip_manager.get_all_trips()` -> returns trips
5. Sets `self._published_trips = all_trips_list` (line 1226)
6. Calls `await self.update_charging_power()` (line 1228)
7. `update_charging_power()` checks if power changed -> if yes, calls `publish_deferrable_loads(self._published_trips, new_power)`
8. `publish_deferrable_loads()` with non-empty trips -> calls `async_publish_all_deferrable_loads`
9. This repopulates the cache

So even if the listener fires early, the cache would still be populated (step 9). No bug.

**UNLESS** the listener fires during a second HA restart cycle, after `_published_trips` is set but before the coordinator data is read. In that case:

1. Listener fires
2. `_published_trips` IS set (from previous publish)
3. `update_charging_power()` is called
4. If power CHANGED between restarts, it republishes
5. `publish_deferrable_loads(self._published_trips)` -> repopulates cache
6. Cache is fine

**If power didn't change**: `update_charging_power` returns early (line 2161: `if new_power == self._charging_power_kw: return`). No republish. Cache is fine.

### Bug 3: `async_publish_all_deferrable_loads` is called with empty trips

This is the most likely root cause. Let me check every path that could call `async_publish_all_deferrable_loads` with an empty `trips` list during startup:

1. **Direct call from `publish_deferrable_loads`** (line 150): passes trips from `_get_all_active_trips()`. If no active trips, `trips=[]`.

2. **From `_handle_config_entry_update`**: calls `update_charging_power()`, which calls `publish_deferrable_loads(self._published_trips)`. If `_published_trips` is empty, clears cache.

3. **From `update_charging_power`** directly: same as #2.

The critical question is: can `_handle_config_entry_update` fire with `_published_trips = []`?

The listener is registered at line 145: `emhass_adapter.setup_config_entry_listener()`. At this point, `self._published_trips = []` (empty, never set).

If `add_update_listener` fires the callback immediately (despite HA source saying it doesn't), then:
1. Listener fires
2. `_published_trips` is empty
3. Gets trips from `trip_manager.get_all_trips()` -> should have trips
4. Sets `_published_trips` to trips list
5. Calls `update_charging_power()` -> republishes trips
6. Cache is populated

But if `get_all_trips()` returns empty (trips not loaded yet), then `_published_trips` stays empty, and `update_charging_power` may publish empty trips.

### The Actual Root Cause

I've identified the most likely root cause through process of elimination:

**The initialization order in `__init__.py` creates a window where `coordinator.data` is read BEFORE the EMHASS cache is populated.**

Here's the exact sequence that causes the bug:

1. Line 134: `trip_manager.async_setup()` -> `publish_deferrable_loads()` -> early return (no adapter)
2. Line 150: `trip_manager.publish_deferrable_loads()` -> populates cache, calls `await coordinator.async_refresh()`
3. `async_refresh()` schedules the update and returns
4. Line 152: coordinator created
5. Line 154: `async_config_entry_first_refresh()` -> may read from cache before it's populated
6. Line 179: sensors set up, read from `coordinator.data`

The window between steps 3 and 5 is the problem. `async_refresh()` at step 2 may not have completed `self.data = await self._async_update_data()` by the time step 5 runs.

Actually, `async_refresh()` DOES await the data fetch. So `self.data` IS set by step 3 completion.

**The bug must be that something ELSE clears `self.data` or the cache between step 3 and step 5.**

The only candidate is the config entry listener. If it fires between steps 3 and 5, it could clear the cache.

But `add_update_listener` doesn't fire the listener. So this shouldn't happen.

**Unless HA calls `ConfigEntry.async_update()` during the restart process, which WOULD fire all listeners.**

This is the most likely explanation:

**During HA restart, `ConfigEntry.async_update()` is called as part of the config entry reload process. This fires the EMHASS adapter's update listener, which calls `_handle_config_entry_update() -> update_charging_power() -> publish_deferrable_loads(self._published_trips)`. At this point, `self._published_trips` is still empty (hasn't been set by any previous publish), so `publish_deferrable_loads([])` clears the cache.**

Then when `async_publish_all_deferrable_loads` is eventually called (line 150), it repopulates the cache. But by the time the sensor reads the data, `coordinator.data` may have already been set by a refresh that happened before the cache was repopulated.

## Recommendations

1. **Move `async_config_entry_first_refresh()` BEFORE the EMHASS adapter setup block** in `__init__.py`. This ensures the first refresh always runs with a known state (empty EMHASS keys). The subsequent `publish_deferrable_loads()` call will trigger a refresh with the correct populated data.

2. **Add defensive code in `_handle_config_entry_update`**: Before calling `update_charging_power()`, check if `_cached_per_trip_params` is empty and the trips haven't been published yet. If so, skip the update.

3. **Add a guard in `async_publish_all_deferrable_loads`**: Before clearing the cache for empty trips, check if there are trips in storage that haven't been published yet. If so, don't clear.

4. **Consider using `async_request_refresh()` instead of `async_refresh()`**: `async_request_refresh()` is debounced but ensures immediate update. However, it may introduce its own race conditions.

5. **Add logging to confirm the root cause**: Add `_LOGGER.warning()` calls before and after each key step in the initialization flow to identify exactly where the data gets cleared.

## Verification Steps

To confirm the bug:

1. Add logging to `async_publish_all_deferrable_loads` to log when the cache is populated vs cleared
2. Add logging to `_handle_config_entry_update` to log when it fires and what `_published_trips` contains
3. Add logging to `async_config_entry_first_refresh` to log what `self.data` contains when it reads from the cache
4. Check HA logs for `ConfigEntry.async_update` calls during restart

## Open Questions

- Does `ConfigEntry.async_update()` fire listeners during HA restart? (Needs HA source verification)
- Does `add_update_listener` fire the listener immediately in the user's HA version? (Source says no, but version-dependent)
- Are there other HA lifecycle hooks that could trigger `_handle_config_entry_update` during restart?
