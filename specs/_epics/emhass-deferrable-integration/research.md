# Research: emhass-deferrable-integration

## Validation Findings

### Spec 1: SOC Integration Baseline

**Can it be built independently?** YES

**Findings:**
- `TripManager.async_get_vehicle_soc()` exists and reads SOC from configured sensor (`trip_manager.py:879-900`)
- `PresenceMonitor` monitors home/plugged status but NOT SOC changes
- No SOC change listener exists in codebase - this spec requires new HA event listener via `async_track_state_change_event`
- Confirmed gap: "No SOC change listener exists" per `.research-codebase.md:290`

**Interface Contract Assessment:**
- Input: State changes from home/plugged/SOC sensors - CORRECT, matches HA patterns
- Output: Calls `trip_manager.async_generate_power_profile()` and `trip_manager.async_generate_deferrables_schedule()` - CORRECT
- Trigger conditions (home+plugged, SOC change) - CORRECT

**Risk:** Debouncing SOC changes not specified. SOC sensors can be noisy (report every few seconds). Recommend adding delta threshold (e.g., 5% change).

---

### Spec 2: Charging Window Calculation

**Do interface contracts make sense given actual code structure?** PARTIALLY

**Findings:**
- `calcular_ventana_carga()` interface contract specified but function does NOT exist in codebase
- Current `trip_manager._get_trip_time()` handles single trip timing but NOT return-to-home tracking
- **CRITICAL GAP**: No code tracks when car RETURNED home. `PresenceMonitor.async_check_home_status()` only reports current state, not return timestamp
- Window calculation requires `hora_regreso` (return time) but this data is not captured

**Interface Contract Assessment:**
- Function signature defined in epic - NEW function needed
- Returns window hours, kWh needed, sufficiency flag - logically sound
- Multi-trip window chaining described correctly

**Missing dependency:** Cannot calculate window without knowing when car returns. Spec 1 should include return-time detection.

---

### Spec 3: SOC Milestone Algorithm

**Are there hidden shared modules needed?** YES

**Findings:**
- `calcular_hitos_soc()` interface contract specified but function does NOT exist in codebase
- Algorithm requires `calcular_ventana_carga()` from Spec 2 - dependency chain correct
- Current code has no deficit propagation logic

**Hidden Dependencies:**
1. **Charging rate calculation**: `charging_power_kw / battery_capacity_kwh * 100` = % SOC/hour. `battery_capacity_kwh` is in config but not currently passed to power profile calculation
2. **Buffer percentage**: Epic says 10% buffer, `const.py` has `DEFAULT_SAFETY_MARGIN = 10` - matches
3. **Trip sorting**: Must sort trips by departure time first - current `async_generate_power_profile()` sorts by deadline, may need enhancement

**Interface Contract Assessment:**
- Function signature and return format - logically sound
- Algorithm example in epic matches described behavior

---

### Spec 4: EMHASS Sensor Enhancement

**Is scope realistic for estimated size?** YES

**Findings:**
- `EmhassDeferrableLoadSensor` exists in `sensor.py:456-574` with `power_profile_watts` and `deferrables_schedule` attributes
- Current sensor state is "ready" | "error" - epic wants to add "active" state
- Index stability issue: `emhass_adapter.py` reuses released indices immediately (`async_release_trip_index()` adds to `_available_indices`)

**Enhancements Needed:**
1. Add `last_update` attribute to sensor
2. Add `emhass_status` attribute to sensor
3. Stable index assignment (don't reuse deleted trip indices immediately)
4. Index reassignment when trips are deleted (maintain EMHASS schedule stability)

**Interface Contract Assessment:**
- Sensor attributes format - mostly correct, minor differences
- `deferrables_schedule` format in epic matches current implementation
- Trigger conditions match existing `EmhassDeferrableLoadSensor.async_update()` flow

---

### Spec 5: Trip Card Enhancement

**Dependencies correctly identified?** YES

**Findings:**
- `TripSensor` exists in `sensor.py:576-706` but does NOT have:
  - `p_deferrable_index` attribute
  - `charging_window` attribute
  - `soc_target` attribute
  - `deficit_from_previous` attribute
- These attributes must be added to `TripSensor._attr_extra_state_attributes`

**Interface Contract Assessment:**
- Trip card additional attributes format - correctly specified
- Dependencies (Spec 4 first) - CORRECT, sensor must publish before trip card can display

**Note:** Trip card enhancement is UI display - depends on backend (Spec 4) providing data.

---

### Spec 6: Automation Template

**Can it work independently?** NO - depends on Spec 4

**Findings:**
- `schedule_monitor.py` exists and handles EMHASS schedule monitoring
- **NAMING MISMATCH**: Epic references `sensor.emhass_plan_{vehicle}_mpc_congelado` but `schedule_monitor.py:111` uses `sensor.emhass_deferrable{emhass_index}_schedule`
- Epic automation template structure is correct HA automation format
- The sensor naming discrepancy needs resolution

**Interface Contract Assessment:**
- Automation reads `p_deferrable{n}` for current hour - CORRECT EMHASS pattern
- Manual mode override via `input_boolean` - standard HA pattern
- `potencia_planificada > 100` threshold - reasonable (100W minimum)

**Risk:** The epic references `sensor.emhass_plan_{vehicle}_mpc_congelado` which appears to be a different sensor format than what `schedule_monitor.py` monitors. Need to clarify actual EMHASS response sensor naming.

---

### Spec 7: Integration with fixes

**Are all integration points captured?** UNCLEAR

**Findings:**
- Epic says it integrates US-6, US-7, US-8, US-9, US-10 from "ev-trip-planner-integration-fixes"
- The `ev-trip-planner-integration-fixes/requirements.md` has:
  - US-1 through US-5 (original 5 bugs)
  - US-6 through US-10 in an "Extended Scope" section at bottom
- Naming confusion: The epic's US-6 is actually the Extended Scope's US-6 (Display p_deferrable Schedule on Trip Cards)
- **EMHASS-specific user stories to integrate:**
  - US-6: Display p_deferrable schedule on trip cards
  - US-7: EMHASS JSON format transformation
  - US-8: Automation template for charge control
  - US-9: Improved charging window calculation
  - US-10: SOC-based trip planning

**Integration Points Captured:**
- `TripManager` -> `EMHASSAdapter` initialization - YES, via `set_emhass_adapter()`
- Sensor creation/deletion synced with vehicle CRUD - PARTIAL, sensors created but no cascade delete
- Dashboard data refresh on trip state changes - YES

---

## Missing Specs

### Missing 1: Return Time Detection
**Description:** The epic calculates charging windows from when the car "returns home" but no code tracks return TIME. Only current home status is tracked, not return timestamp.

**Impact:** Spec 2 (Charging Window Calculation) cannot be fully implemented without this.

**Recommendation:** Add a `last_return_time` tracking to `PresenceMonitor` or create new `ReturnMonitor` component.

### Missing 2: Index Stability (Not Really a Spec, but a Gap)
**Description:** When a trip is deleted, its index is immediately released and can be reused. EMHASS may still reference the old index. The epic mentions "stability" but doesn't explicitly address how indices are kept stable.

**Current behavior:** `emhass_adapter.py:127-129` - index released, added back to available pool, reused by next new trip.

**Recommendation:** Consider "soft delete" - don't reuse indices for X hours, or require explicit reassignment.

---

## Unnecessary Specs

### None identified

All 7 specs address real gaps in the codebase. No spec appears to duplicate existing functionality.

---

## Dependency Graph Issues

**Corrected dependency chain based on codebase analysis:**

```
Spec 1 (SOC Integration Baseline)
         |
         v
Spec 2 (Charging Window Calculation) --> Missing: Return Time Detection
         |
         v
Spec 3 (SOC Milestone Algorithm)
         |
         v
Spec 4 (EMHASS Sensor Enhancement) --> Missing: Stable Index Assignment
         +-----------+
         |           |
         v           v
Spec 5 (Trip Card)  Spec 6 (Automation Template)
         |           |
         +-----+-----+
               |
               v
    Spec 7 (Integration)
```

**Additional edge found:** Spec 5 (Trip Card) may need direct access to `EmhassDeferrableLoadSensor` data, not just through `TripManager`. Currently `TripSensor` does not have access to EMHASS index data.

---

## Additional Risks

1. **Schedule Monitor mismatch**: `schedule_monitor.py` uses `sensor.emhass_deferrable{index}_schedule` but epic automation uses `sensor.emhass_plan_{vehicle}_mpc_congelado`. Need to verify actual EMHASS sensor naming.

2. **SOC sensor availability**: If SOC sensor is unavailable, `async_get_vehicle_soc()` returns 0.0. Spec 1 should handle this gracefully (maybe skip recalculation if SOC unavailable).

3. **Multi-vehicle coordination**: Each vehicle has separate EMHASS indices. If multiple vehicles share same EMHASS instance, index pools must be coordinated.

4. **Battery capacity access**: `battery_capacity_kwh` is in config but not consistently passed to `async_generate_power_profile()`. Spec 3 needs this value.

---

## Summary Assessment

| Spec | Independent? | Interface Contract | Dependencies | Risk Level |
|------|--------------|-------------------|--------------|------------|
| 1 | YES | Valid | None | Medium (debouncing) |
| 2 | NO | Gap (no return time) | Spec 1 | HIGH (missing data) |
| 3 | NO | Valid | Spec 2 | Medium (needs battery_capacity) |
| 4 | YES | Mostly valid | Spec 3 | Low |
| 5 | NO | Valid | Spec 4 | Low |
| 6 | NO | Naming mismatch | Spec 4 | Medium (sensor naming) |
| 7 | NO | Naming confusion | All | Medium (integration scope) |

**Overall:** The decomposition is sound but has gaps in Spec 2 (missing return-time tracking) and unresolved sensor naming questions for Spec 6.
