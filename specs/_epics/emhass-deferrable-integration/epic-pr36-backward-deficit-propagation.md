# Epic: Backward Charge Deficit Propagation (PR #36)

## Vision

When a trip needs more charging hours than its window allows, the excess must propagate BACKWARD to previous trips. Currently, overflow is silently discarded — trip #3 needs 3h but only has 2h → 1h vanishes. With backward propagation, that 1h is added to trip #2's window (if it has spare capacity), then to trip #1, etc.

This ensures trips get charged even when individual windows are too short.

---

## Success Criteria

1. Trip needing 3h charging with 2h window → 1h deficit propagates to previous trip
2. Chain propagation: trip 3 deficit → trip 2 → trip 1 (last to first)
3. EMHASS scheduling parameters (`def_total_hours`) reflect propagated hours
4. `def_total_hours_array` sensor attributes show correct propagated values
5. Integration test demonstrates chain propagation with 3 trips

---

## Dependency Graph

```
[Spec A: calculate_hours_deficit_propagation()]
         |
         v
[Spec B: Wire into emhass_adapter.py batch loop]
         |
         v
[Spec C: Integration test]
```

All specs are vertical slices of the same user value: "ensuring every trip gets its required charging."

---

## Spec A: Pure Backward Hours Deficit Propagation Function

### Goal (User Story)

As a calculation function, I need to walk backward through charging windows and add excess charging needs to previous trips so no deficit is lost.

### Problem

`calculate_multi_trip_charging_windows()` allocates windows sequentially but does not handle the case where a trip's `horas_carga_necesarias > ventana_horas`. The missing hours are silently discarded.

`calculate_deficit_propagation()` exists (lines 608-750 of calculations.py) but operates in the SOC domain — it adjusts `soc_objetivo` values for display/sensor attributes. It does NOT adjust `def_total_hours` for EMHASS scheduling.

The SOC propagation and EMHASS scheduling are completely decoupled.

### Acceptance Criteria

1. **Given** windows from `calculate_multi_trip_charging_windows()`, **when** trip N needs more hours than its window, **then** the excess (horas_carga_necesarias - ventana_horas) is added to trip N-1's deficit_accumulated_hours
2. **Given** trip N-1 already has propagated deficit, **when** excess from trip N arrives, **then** it accumulates (adds to existing deficit_acumulado_hours)
3. **Given** deficit reaches trip 0 (first trip), **when** there is no previous trip, **then** the deficit remains as unpropagated overflow (returned in result)
4. **Given** all trips have sufficient windows, **when** function runs, **then** returned windows match input windows (no-op case)
5. **Given** a trip has ventana_horas=2 and horas_carga_necesarias=3, **when** processing, **then** deficit_acumulado_hours=1 is propagated to previous trip
6. **Given** the function receives empty windows list, **when** called, **then** returns empty list

### Interface Contracts

**Function signature:**
```python
def calculate_hours_deficit_propagation(
    windows: List[Dict[str, Any]],
    charging_power_kw: float,
    battery_capacity_kwh: float,
) -> List[Dict[str, Any]]:
    """Walk backward through windows and propagate excess charging hours.

    For each trip (last to first):
    - If horas_carga_necesarias > ventana_horas, the excess propagates to
      the previous trip as additional deficit_hours that must be charged.

    Args:
        windows: List of window dicts from calculate_multi_trip_charging_windows().
                 Each must have "ventana_horas", "horas_carga_necesarias", "trip".
        charging_power_kw: Charging power in kW (for SOC→kWh conversion).
        battery_capacity_kwh: Battery capacity in kWh (for SOC→kWh conversion).

    Returns:
        List of window dicts with same structure as input, PLUS:
        - "deficit_hours_propagated": float — total hours propagated INTO this trip
        - "deficit_hours_original": float — hours that could NOT be propagated (overflow at trip 0)
        - "deficit_hours_to_propagate": float — hours this trip is pushing forward (to previous)
        - "adjusted_def_total_hours": int — original def_total_hours + deficit_hours_propagated

    If a window has es_suficiente=True, it gets deficit_hours_propagated=0.
    If a window has es_suficiente=False, deficit_hours_to_propagate =
        horas_carga_necesarias - ventana_horas.
    """
```

**Return structure per window:**
```python
{
    "ventana_horas": 2.0,
    "horas_carga_necesarias": 3.0,
    "es_suficiente": False,
    "deficit_hours_propagated": 0.5,      # hours added from NEXT trip
    "deficit_hours_to_propagate": 1.0,     # hours this trip pushes to PREVIOUS
    "adjusted_def_total_hours": 4,         # ceil(original + propagated)
}
```

**Algorithm:**
```
1. Walk windows in REVERSE order (last index to 0)
2. For each window at position i:
   a. If es_suficiente == True: deficit_to_propagate = 0
   b. If es_suficiente == False:
      deficit_to_propagate = horas_carga_necesarias - ventana_horas
      If deficit_to_propagate > 0:
          If i > 0:  # there is a previous trip
              windows[i-1]["incoming_deficit"] += deficit_to_propagate
          else:
              windows[0]["unpropagated_overflow"] += deficit_to_propagate
3. For each window at position i:
   a. deficit_hours_propagated = windows[i].get("incoming_deficit", 0)
   b. deficit_hours_original = windows[i].get("unpropagated_overflow", 0)
   c. Adjusted def_total_hours = ceil(original_def_total_hours + deficit_hours_propagated)
4. Return enriched windows list
```

### Dependencies

None. Pure function, no external imports beyond calculations.py's existing deps.

### Size

Small — ~60 lines of pure logic. Can be implemented in 1 commit.

---

## Spec B: Wire Propagation into EMHASS Adapter Batch Loop

### Goal (User Story)

As the EMHASS adapter, I need to run the backward propagation after computing batch windows and before populating per-trip cache entries, so that `def_total_hours` reflects propagated deficits.

### Problem

At lines 862-873 of emhass_adapter.py:
```python
windows = calculate_multi_trip_charging_windows(...)
for i, (trip_id, _, _) in enumerate(trip_deadlines):
    if i < len(windows):
        batch_charging_windows[trip_id] = windows[i]
```

Windows are passed directly to `_populate_per_trip_cache_entry` without propagation. Inside that method (lines 634-642):
```python
window_size = def_end_timestep - def_start_timestep
if total_hours > window_size:
    _LOGGER.warning("Capping total_hours from %.1f to window size %.1f for trip %s",
                    old_total_hours, window_size, trip_id)
    total_hours = window_size  # <-- discards overflow
```

The overflow that should have been propagated is silently capped to window_size, causing the deficit to vanish entirely.

### Acceptance Criteria

1. **Given** batch windows computed from `calculate_multi_trip_charging_windows()`, **when** `calculate_hours_deficit_propagation()` runs, **then** returned windows have `deficit_hours_propagated` and `adjusted_def_total_hours` populated
2. **Given** propagated windows, **when** `batch_charging_windows[trip_id]` is populated, **then** the entry uses the propagated window (not raw window)
3. **Given** a propagated window with `adjusted_def_total_hours`, **when** `_populate_per_trip_cache_entry` runs with `pre_computed_fin_ventana`, **then** `def_total_hours` in the cache entry equals `adjusted_def_total_hours` (not the capped original)
4. **Given** the capping guard (lines 638-642) runs, **when** `adjusted_def_total_hours > window_size`, **then** the warning still fires but the adjusted value is preserved (EMHASS handles the schedule, the capping was the original bug)
5. **Given** no trips or empty windows, **when** batch computation runs, **then** the flow is a no-op (empty list returned)

### Interface Contracts

**New call site in `emhass_adapter.py:async_publish_all_deferrable_loads()` at line 874:**
```python
# NEW: Propagate hours deficits backward through trips
from .calculations import calculate_hours_deficit_propagation

propagated_windows = calculate_hours_deficit_propagation(
    windows=windows,
    charging_power_kw=charging_power_kw,
    battery_capacity_kwh=self._battery_capacity_kwh,
)

# Replace raw windows with propagated ones
for i, (trip_id, _, _) in enumerate(trip_deadlines):
    if i < len(propagated_windows):
        batch_charging_windows[trip_id] = propagated_windows[i]
```

**Capping guard change at lines 638-642:**
```python
# OLD (discard overflow):
if total_hours > window_size:
    total_hours = window_size

# NEW (keep adjusted value, log warning):
# The adjusted value comes from calculate_hours_deficit_propagation()
# and represents hours that need to be charged in a window that's too short.
# EMHASS can handle def_total_hours > window_size — it will schedule
# the maximum it can within the available timeframe.
if total_hours > window_size:
    _LOGGER.warning(
        "Trip %s needs %.1f hours but window is only %.1fh. "
        "Sending adjusted def_total_hours to EMHASS (it will cap at window).",
        trip_id, total_hours, window_size
    )
# Do NOT cap — let EMHASS handle it with the full request
```

**Import addition at top of emhass_adapter.py:**
```python
from .calculations import calculate_hours_deficit_propagation, calculate_multi_trip_charging_windows
```

### Dependencies

Spec A: `calculate_hours_deficit_propagation()` must exist in `calculations.py`.

### Size

Medium — ~30 lines of wiring plus the capping guard change. Can be implemented in 1-2 commits.

---

## Spec C: Integration Test — Backward Deficit Propagation

### Goal (User Story)

As a tester, I need an integration test that verifies deficit propagation works end-to-end through the EMHASS adapter, demonstrating that a trip with insufficient window causes charging hours to propagate to previous trips.

### Acceptance Criteria

1. **Given** 3 trips ordered by departure time where:
   - Trip #1: 4h window, needs 3h charging (sufficient)
   - Trip #2: 2h window, needs 3h charging (deficit = 1h)
   - Trip #3: 1h window, needs 3h charging (deficit = 2h)
   **when** `calculate_hours_deficit_propagation()` runs
   **then**:
   - Trip #3 gets deficit_hours_propagated=0, deficit_hours_to_propagate=2
   - Trip #2 gets deficit_hours_propagated=2 (from #3), deficit_hours_to_propagate=1
   - Trip #1 gets deficit_hours_propagated=3 (2 from #3 + 1 from #2), deficit_hours_to_propagate=0

2. **Given** propagated windows, **when** `batch_charging_windows` is populated
   **then** each trip_id maps to the correct propagated window dict

3. **Given** propagated cache entries, **when** `def_total_hours` is read from each entry
   **then** trip #1 has the highest value (original + all propagated), trip #2 medium, trip #3 lowest

4. **Given** all trips have sufficient windows, **when** propagation runs
   **then** all `deficit_hours_propagated=0`, `deficit_hours_to_propagate=0`

5. **Given** single trip with deficit, **when** propagation runs
   **then** deficit_hours_to_propagate=excess, unpropagated_overflow=excess (no previous trip to propagate to)

### Test Structure

```
tests/test_hours_deficit_propagation.py
├── test_calculate_hours_deficit_propagation_basic()           # Spec A
├── test_calculate_hours_deficit_propagation_chain()           # Spec A (chain)
├── test_calculate_hours_deficit_propagation_no_op()           # Spec A (all sufficient)
├── test_calculate_hours_deficit_propagation_single_trip()     # Spec A (no prev trip)
├── test_adapters_batch_propagation_wiring()                   # Spec B
├── test_cache_entry_uses_propagated_hours()                   # Spec B
├── test_capping_guard_preserves_adjusted_hours()              # Spec B
└── test_integration_full_flow()                               # End-to-end
```

### Dependencies

Spec A and Spec B must be implemented (tests verify the implementation).

### Size

Medium — 8 test functions. Can be implemented in 1 commit.

---

## Advisory Architecture

### Data Flow

```
calculate_multi_trip_charging_windows()
    │
    ├── returns: raw windows [w1, w2, w3]
    │
    ▼
calculate_hours_deficit_propagation(windows)    ← NEW
    │
    │   Walk backward: w3 deficit → w2, w2 deficit → w1
    │
    ├── returns: propagated windows [w1', w2', w3']
    │        w1'.adjusted_def_total_hours = w1.def_total_hours + deficit_from_w2
    │        w2'.adjusted_def_total_hours = w2.def_total_hours + deficit_from_w3 - w2.own_deficit
    │        w3'.adjusted_def_total_hours = w3.def_total_hours (no previous trip)
    │
    ▼
_batch_charging_windows[trip_id] = w_i'    (propagated, not raw)
    │
    ▼
_populate_per_trip_cache_entry(w_i')
    │
    ├── uses: w_i'.adjusted_def_total_hours for cache entry
    │
    └── result: cache["def_total_hours"] = adjusted_def_total_hours
         cache["def_total_hours_array"] = [adjusted_def_total_hours]
```

### Key Insight

The propagation function does NOT modify `ventana_horas`. It modifies `def_total_hours` — the scheduling parameter. EMHASS receives the request for X hours but can only schedule them in the available window. The deficit remains visible in the sensor attributes (`def_total_hours_array`) even if EMHASS can't fully schedule it. This is the correct behavior — it communicates the need even when the window is insufficient.

### Relationship to Existing `calculate_deficit_propagation()`

| Aspect | `calculate_deficit_propagation()` (existing) | `calculate_hours_deficit_propagation()` (new) |
|--------|---------------------------------------------|---------------------------------------------|
| Domain | SOC percentage | Charging hours (EMHASS scheduling) |
| Adjusts | `soc_objetivo` | `def_total_hours` |
| Used by | Sensor attributes, display | EMHASS power profile |
| Output field | `soc_objetivo_ajustado` | `adjusted_def_total_hours` |

They serve different consumers. The new function fills the gap: scheduling parameters were not being adjusted.

---

## Risk Assessment

1. **EMHASS response to def_total_hours > window_size**: EMHASS may reject or warn when the requested hours exceed the available window. The capping guard change logs the situation without discarding the value — EMHASS itself handles the constraint.

2. **Chain reaction depth**: With many trips, deficits cascade backward. Each propagation step adds to the previous trip's need. For N trips, the first trip could receive deficit from all subsequent trips. This is correct behavior — the first trip should charge the most.

3. **Backward compatibility**: The new function is added to `calculations.py` exports. It does NOT modify any existing function signatures or behaviors. The adapter wiring is additive.

4. **Test mocking complexity**: The EMHASS adapter test needs to mock the trip data such that window sizes and charging needs create the desired deficit pattern. The `calculate_multi_trip_charging_windows()` function should be mocked to return pre-configured windows.

---

## Implementation Order

1. **Spec A** first — pure function, no dependencies, easy to test in isolation
2. **Spec C** (tests for A) alongside Spec A — TDD on the pure function
3. **Spec B** — wire propagation into adapter, adjust capping guard
4. **Spec C** (tests for B) — integration tests for wiring

Total: 3-5 commits, 2-4 hours of work.
