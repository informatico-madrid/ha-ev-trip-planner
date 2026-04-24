# Design: Propagate Charge Deficit Algorithm (Spec A)

## Overview

Add `calculate_hours_deficit_propagation()` to `calculations.py` — a pure function that walks backward through charging windows and propagates unmet charging hours to earlier trips with spare capacity.

## Algorithm

```python
def calculate_hours_deficit_propagation(
    windows: list[dict],
    battery_capacity_kwh: float,
    def_total_hours: list[float] | None = None,
) -> list[dict]:
    """Walk backward from last trip to first.

    For each trip:
    1. If horas_carga_necesarias > ventana_horas → deficit = excess
    2. Propagate deficit backward to previous trip (if it has spare capacity)
    3. Track absorbed hours and remaining deficit per trip
    """
```

**Key decisions:**

1. **`def_total_hours` as optional parameter**: Window dicts from `calculate_multi_trip_charging_windows()` do NOT contain `def_total_hours`. If not provided, default to `horas_carga_necesarias` from the window dict.

2. **Spare capacity = `ventana_horas - def_total_hours`**: A trip can absorb deficit up to its unused window capacity (floored at 0).

3. **Walk order**: Last trip → first trip (strict backward, no cycles).

4. **`deficit_hours_to_propagate` on last trip = 0**: The last trip's own overflow is the starting deficit, not "to propagate". It's absorbed by the previous trip.

5. **`deficit_hours_to_propagate` on first trip = remaining deficit after all absorption**: The first trip has no predecessor, so any deficit it couldn't absorb stays here.

6. **`deficit_hours_propagated` per trip = hours absorbed from the NEXT trip only** (not cumulative from all later trips).

## Function Signature

```python
def calculate_hours_deficit_propagation(
    windows: list[dict],
    battery_capacity_kwh: float,
    def_total_hours: list[float] | None = None,
) -> list[dict]:
    """Calculate charging windows with backward hours deficit propagation.

    Args:
        windows: List of window dicts from calculate_multi_trip_charging_windows().
            Must contain: ventana_horas, horas_carga_necesarias.
        battery_capacity_kwh: Battery capacity for reference.
        def_total_hours: Optional list of total charging hours per trip.
            If None, defaults to horas_carga_necesarias from each window.

    Returns:
        List of enriched window dicts with additional keys:
        - deficit_hours_propagated: hours absorbed from next trip (float, 2dp)
        - deficit_hours_to_propagate: remaining deficit (float, 2dp)
        - adjusted_def_total_hours: original def_total_hours + absorbed (float, 2dp)
    """
```

## Algorithm Pseudocode

```
1. N = len(windows)
2. If N == 0: return []
3. Initialize def_total_hours list (from param or windows)
4. Initialize results list
5. Initialize deficit_carrier = 0.0 (accumulated deficit from trips after current)
6. For i from N-1 down to 0:
    a. ventana = windows[i]["ventana_horas"]
    b. horas_carga = windows[i]["horas_carga_necesarias"]
    c. original_def_total = def_total_hours[i] if def_total_hours else horas_carga
    d. spare = max(0.0, ventana - original_def_total)

    e. # How much of the carrier deficit can this trip absorb?
    f. absorbed = min(deficit_carrier, spare)
    g. deficit_carrier = deficit_carrier - absorbed

    h. # If this trip itself has deficit (needs more than window allows)?
    i. own_deficit = max(0.0, horas_carga - ventana)
    j. deficit_carrier += own_deficit

    k. # Store results
    l. result[i] = dict(windows[i])  # copy
    m. result[i]["deficit_hours_propagated"] = round(absorbed, 2)
    n. result[i]["deficit_hours_to_propagate"] = round(deficit_carrier, 2)
    o. result[i]["adjusted_def_total_hours"] = round(original_def_total + absorbed, 2)

7. Return results
```

## Test Scenarios

| Scenario | Input | Expected Output |
|----------|-------|-----------------|
| No deficit | All `ventana >= horas_carga` | All propagation fields = 0 |
| Last trip deficit, middle has spare | Trip 3: deficit 1h, Trip 2: spare 4h | Trip 3: absorbed=1h, to_prop=0 |
| Chain propagation | Trip 3: deficit 3h, Trip 2: spare 2h, Trip 1: spare 4h | Trip 3: abs=0, to_prop=1h; Trip 2: abs=2h, to_prop=0; Trip 1: abs=1h |
| Single trip deficit | 1 trip: needs 5h, has 2h window | abs=0, to_prop=3h |
| First trip overflow | First trip needs 5h, has 2h | First trip shows to_prop=3h |
| Empty input | [] | [] |

## Existing Tests to Verify Unchanged

- `test_calculations.py` — all `test_multi_trip_charging_windows_*` tests
- `test_calculations.py` — all `test_deficit_*` tests (SOC propagation)
- Any test that imports `calculate_hours_deficit_propagation` should fail gracefully (function doesn't exist yet)
