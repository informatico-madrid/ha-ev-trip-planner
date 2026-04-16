# Research: Fix Sequential Trip Charging Bug

**Spec**: fix-sequential-trip-charging
**Date**: 2026-04-16
**Status**: Updated (User Observation)

---

## Executive Summary

**User's Observation**: The aggregated sensor shows:
```
def_start_timestep_array: 0, 0       # BUG: Trip 2 should start after Trip 1 + buffer
def_end_timestep_array: 11, 49       # CORRECT
def_total_hours_array: 8, 46         # User unsure, needs verification
p_deferrable_matrix: [correct values] # CORRECT
```

**Root Cause**: In `emhass_adapter.py:363-368`, `calculate_multi_trip_charging_windows()` is called with **only one trip at a time**:
```python
charging_windows = calculate_multi_trip_charging_windows(
    trips=[(deadline_dt, trip)],  # Only ONE trip!
    soc_actual=soc_current,
    hora_regreso=hora_regreso,
    charging_power_kw=self._charging_power_kw,
    duration_hours=6.0,  # HARDCODED RETURN BUFFER!
)
```

And `async_publish_all_deferrable_loads()` (line 634) calls this **for each trip individually** via a loop. The multi-trip function never receives both trips together.

**Key Finding**: The `duration_hours=6.0` parameter is being used as a **return buffer** by `calculate_multi_trip_charging_windows()`. Each trip gets its own `def_start_timestep` computed in isolation (always ~0 for next trip), and the arrays are aggregated by extending each trip's single-element arrays.

**Feasibility**: High | **Risk**: Low | **Effort**: S

---

## 1. Code Flow Analysis

### Where Arrays Are Built (sensor.py:254-257)

```python
if "def_start_timestep_array" in params:
    def_start_timestep_array.extend(params["def_start_timestep_array"])
```

The aggregated sensor reads `def_start_timestep_array` from **each trip's cached params** and extends the list. This means:
- Trip 0 cache: `def_start_timestep_array: [0]` → added to array
- Trip 1 cache: `def_start_timestep_array: [0]` → added to array
- Result: `[0, 0]`

### Where Cache Is Populated (emhass_adapter.py:553-563)

```python
self._cached_per_trip_params[trip_id] = {
    ...
    "def_start_timestep": def_start_timestep,  # Computed per-trip in isolation
    "def_end_timestep": def_end_timestep,
    ...
    "def_start_timestep_array": [def_start_timestep],  # Single-element list!
    "def_end_timestep_array": [def_end_timestep],
}
```

Each trip's cache has **single-element arrays** (wrapping the per-trip value). The aggregation works by extending these single-element arrays into a multi-trip array.

### The Multi-Trip Function (calculations.py:339-421)

**Signature**:
```python
def calculate_multi_trip_charging_windows(
    trips: List[Tuple[datetime, Dict[str, Any]]],
    soc_actual: float,
    hora_regreso: Optional[datetime],
    charging_power_kw: float,
    duration_hours: float = 6.0,  # <-- This is the RETURN BUFFER!
) -> List[Dict[str, Any]]:
```

**Designed behavior**: When called with MULTIPLE trips:
- First trip (idx=0): Starts at `hora_regreso` or calculated offset
- Subsequent trips (idx>0): Start at `previous_arrival` + duration buffer

**The Bug**: It's called with **one trip at a time**, so the multi-trip logic never executes.

---

## 2. The Real Problem: Per-Trip Processing

### Current Code Path (BROKEN)

1. `async_publish_all_deferrable_loads()` (emhass_adapter.py:634):
```python
for trip in trips:
    if await self.async_publish_deferrable_load(trip):
```

2. `async_publish_deferrable_load()` (emhass_adapter.py:363-368):
```python
charging_windows = calculate_multi_trip_charging_windows(
    trips=[(deadline_dt, trip)],  # Only ONE trip!
    soc_actual=soc_current,
    hora_regreso=hora_regreso,
    charging_power_kw=self._charging_power_kw,
    duration_hours=6.0,  # HARDCODED 6-hour return buffer
)
```

**Problem**: The multi-trip function receives a list with exactly ONE trip. Its sequential logic (for idx>0) never runs.

### Why def_total_hours Might Be Wrong Too

The user suspects `def_total_hours_array` could also be affected:
- If `def_start_timestep=0` and `def_end_timestep=11` for Trip 1 → duration = 11 hours
- But Trip 1 is supposed to be 8 hours (user's sensor shows `def_total_hours: 8`)
- Similarly for Trip 2: if start=0, end=49 → duration = 49 hours, not 46

**Verification needed**: Check if the `def_end_timestep` calculation accounts for the trip's actual position or if it's also computing from 0.

---

## 3. Trip Data Flow & The Fix Location

### Where All Trips Are Available

`async_publish_all_deferrable_loads()` (emhass_adapter.py:606-728) receives ALL trips and has the perfect place to batch-process them:

```python
async def async_publish_all_deferrable_loads(
    self, trips: List[Dict[str, Any]], charging_power_kw: Optional[float] = None
) -> bool:
    """Process ALL trips together, not one-by-one."""
    for trip in trips:  # Current: processes one at a time
```

### The Fix: Batch Process All Trips

**Option A: Move multi-trip calculation here**
1. Collect all trip datetimes before the per-trip loop
2. Call `calculate_multi_trip_charging_windows()` ONCE with ALL trips
3. Use the returned `inicio_ventana` for each trip's `def_start_timestep`

**Option B: Keep per-trip but calculate offsets**
1. Compute cumulative offset from all previous trips
2. Add offset to each trip's `def_start_timestep`

**Recommended: Option A** — cleaner, uses the existing multi-trip function as designed.

---

## 4. EMHASS Constraint Model

### How EMHASS Interprets `def_start_timestep_array`

- Values are **zero-based timestep indices** from optimization window start
- Index 0 = beginning of optimization window ("now")
- EMHASS enforces: load can ONLY operate between `def_start_timestep` and `def_end_timestep`
- Setting `[0, 0]` means BOTH trips can start immediately → concurrent charging

### Timestep Calculation

```python
# With 60-min timesteps (current project uses hourly):
timesteps_per_hour = 60 / optimization_time_step_minutes

# Example: 8-hour delay with 60-min steps
def_start_timestep = int(8 * 1) = 8
```

**Note**: This project uses hourly timesteps (based on sensor data showing 168 slots = 7 days × 24 hours).

---

## 5. Recommended Fix Approach

### Option A: Batch Process All Trips (RECOMMENDED)

Modify `async_publish_all_deferrable_loads()` to batch-process trips:

```python
async def async_publish_all_deferrable_loads(self, trips, charging_power_kw=None):
    # BEFORE per-trip loop: compute multi-trip charging windows
    charging_windows = calculate_multi_trip_charging_windows(
        trips=[(self._calculate_deadline_from_trip(t), t) for t in trips],
        soc_actual=await self._get_current_soc(),
        hora_regreso=await self._get_hora_regreso(),
        charging_power_kw=charging_power_kw or self._charging_power_kw,
        duration_hours=self._get_return_buffer_hours(),  # Configurable
    )
    
    # Then use charging_windows[i]["inicio_ventana"] for trip i's def_start_timestep
    for i, trip in enumerate(trips):
        window = charging_windows[i]
        def_start_timestep = compute_timestep(window["inicio_ventana"], now)
        # ... rest of per-trip processing with correct def_start_timestep
```

### Option B: Calculate Offsets Inline

Add a `_calculate_sequential_starts()` helper that computes cumulative offsets:

```python
def _calculate_sequential_starts(self, trips) -> List[int]:
    """Calculate def_start_timestep for each trip based on sequential logic."""
    timesteps_per_hour = 1  # 1 timestep = 1 hour (current project uses hourly)
    return_buffer = self._get_return_buffer_hours()  # Configurable, default 4h
    result = [0]
    cumulative_hours = 0.0
    
    for i in range(1, len(trips)):
        prev_duration = trips[i-1].get("duration_hours", 6.0)
        cumulative_hours += prev_duration + return_buffer
        result.append(int(cumulative_hours * timesteps_per_hour))
    
    return result
```

### Return Buffer Configuration

**Current**: Hardcoded `duration_hours=6.0` in line 368
**User's expectation**: 4-6 hours (day trips)
**Recommendation**:
1. Add `return_buffer_hours` config option (default 4.0h)
2. Range: 0-12 hours, step 0.5h
3. Store in entry options, read via `self._config.get("return_buffer_hours", 4.0)`

---

## 6. Files to Modify

| File | Change | Risk |
|------|--------|------|
| `emhass_adapter.py` | Primary fix: batch process trips or add sequential starts helper | Low |
| `calculations.py` | Verify `calculate_multi_trip_charging_windows` handles edge cases | None |
| `sensor.py` | No change needed (already collects arrays correctly) | None |
| `const.py` | Add `CONF_RETURN_BUFFER_HOURS` constant | None |
| `config_flow.py` | Optional: Add return_buffer_hours config option | Low |

---

## 7. Test Strategy

### Unit Tests Needed
- Two sequential trips → `def_start_timestep_array: [0, X]` where X > 0
- Single trip → existing behavior unchanged (`def_start_timestep: 0`)
- Three sequential trips → cumulative offset
- Overlapping trips → buffer constraint respected

### Edge Cases
- Trip 1 duration + buffer exceeds Trip 2 deadline → graceful handling
- Empty trips list → no crash
- Single trip (no sequential processing needed) → backwards compatible

---

## 8. References

- EMHASS docs: [emhass.readthedocs.io](https://emhass.readthedocs.io/en/latest/)
- `calculations.py`: `calculate_multi_trip_charging_windows()` function
- `emhass_adapter.py`: `async_publish_deferrable_load()` and `async_publish_all_deferrable_loads()`
- Related spec: `fix-emhass-aggregated-sensor` (datetime, ceil, flickering fixes)
