# SOC Value Flow Research -- m403-dynamic-soc-capping

## 1. SOC VALUE FLOW DIAGRAM

```
User Config (config_flow.py)
        |
        v
  Config Entry Data (__init__.py:120-188)
  ├── battery_capacity_kwh
  ├── charging_power_kw
  ├── soc_sensor  (entity ID)
  ├── safety_margin_percent
  └── ...
        |
        v
  EMHASSAdapter.__init__ (emhass_adapter.py:57-140)
  ├── _charging_power_kw = entry_data[CONF_CHARGING_POWER]
  ├── _battery_capacity_kwh = entry_data[CONF_BATTERY_CAPACITY]
  └── _safety_margin_percent = entry_data.get("safety_margin_percent")
        |
        v
  SOC reads at runtime:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  EMHASSAdapter._get_current_soc() (emhass_adapter.py:2368-2401)    │
  │    Reads from soc_sensor entity state (float percentage)           │
  │    Returns None if unavailable -> fallback 50.0                    │
  └─────────────────────────────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────────────────────────────┐
  │  trip_manager.py: Calculations entry points:                       │
  │                                                                     │
  │  async_generate_power_profile() (line 1974)                        │
  │    -> calls calculate_power_profile() [calculations.py:1092]       │
  │       Takes: soc_current, battery_capacity_kwh, charging_power_kw  │
  │                                                                     │
  │  async_calcular_energia_necesaria() (line 1433)                    │
  │    -> pure calc: energy_needed = target - current_energy           │
  │                                                                     │
  │  calcular_hitos_soc() (line 1876)                                  │
  │    -> _calcular_soc_objetivo_base() -> calculate_soc_target()      │
  │       -> returns soc_objetivo_base = energia_soc + buffer          │
  │    -> calculate_deficit_propagation() -> soc_objetivo_ajustado     │
  └─────────────────────────────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────────────────────────────┐
  │  calculations.py: Pure calculation functions:                      │
  │                                                                     │
  │  calculate_soc_target() [line 209]                                 │
  │    Input: trip dict, battery_capacity_kwh, consumption, buffer     │
  │    Computes: energia_soc = (kwh / capacity) * 100                 │
  │    Returns: soc_objetivo_base = energia_soc + soc_buffer_percent   │
  │    *** DYNAMIC CAP POINT #1: Apply min(required_soc, dynamic_limit) ***
  │                                                                     │
  │  calculate_energy_needed() [line 307]                              │
  │    Input: trip, capacity, soc_current, charging_power, margin      │
  │    Computes: energia_necesaria = max(0, energia_objetivo - actual)│
  │    Uses: soc_current as starting point                           │
  │    *** DYNAMIC CAP POINT #2: Adjust energia_objetivo via capped SOC ***
  │                                                                     │
  │  determine_charging_need() [line 260]                              │
  │    Calls calculate_energy_needed() -> returns ChargingDecision     │
  │    Uses SOC-aware energy calculation                             │
  │                                                                     │
  │  calculate_deficit_propagation() [line 716]                        │
  │    Input: trips, soc_data, windows, tasa_carga_soc, battery_cap   │
  │    Iterates: reverse order, soc_objetivo + deficits               │
  │    At line 805/842: calls calculate_soc_target()                  │
  │    At line 808: soc_objetivo_ajustado = soc_objetivo + deficit    │
  │    *** DYNAMIC CAP POINT #3: Cap soc_objetivo_ajustado to dynamic_limit ***
  │                                                                     │
  │  calculate_power_profile_from_trips() [line 953]                   │
  │    Input: trips, power_kw, soc_current, battery_capacity          │
  │    At line 1033-1037: calls determine_charging_need()            │
  │    Returns: power profile list (watts per hour)                   │
  │    *** DYNAMIC CAP POINT #4: SOC awareness in power calc ***      │
  │                                                                     │
  │  calculate_power_profile() [line 1092]                             │
  │    Input: all_trips, soc_current, power_kw, battery_cap          │
  │    At line 1166-1169: calls calculate_energy_needed()            │
  │    Returns: power profile (watts per hour)                        │
  └─────────────────────────────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────────────────────────────┐
  │  EMHASSAdapter: Orchestration layer:                               │
  │                                                                     │
  │  async_publish_all_deferrable_loads() [line 781]                   │
  │    1. batch_charging_windows = calculate_multi_trip_charging_windows()
  │    2. projected_soc propagation (line 993-1056)                    │
  │    3. _populate_per_trip_cache_entry() per trip                   │
  │    4. _calculate_power_profile_from_trips()                       │
  │       -> calls calculations.calculate_power_profile_from_trips()  │
  │                                                                     │
  │  _populate_per_trip_cache_entry() [line 542]                       │
  │    1. determine_charging_need() -> ChargingDecision               │
  │    2. deadline calculation                                        │
  │    3. charging_windows computation                                │
  │    4. timestep calculation                                        │
  │    5. power_profile = _calculate_power_profile_from_trips()       │
  │    6. Cache in _cached_per_trip_params                            │
  │    *** DYNAMIC CAP POINT #5: Modify ChargingDecision.kwh_needed ***
  │                                                                     │
  │  publish_deferrable_loads() [line 1156]                            │
  │    1. soc_current = _get_current_soc()                            │
  │    2. power_profile = _calculate_power_profile_from_trips()       │
  │    3. Cache for coordinator                                       │
  │    4. Per-trip cache population                                    │
  └─────────────────────────────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Final output:                                                     │
  │  - _cached_power_profile: List[float] (watts per hour, 168 elements)
  │  - _cached_per_trip_params: Dict[trip_id, params]                 │
  │  - coordinator.data["emhass_power_profile"]                       │
  │  - coordinator.data["per_trip_emhass_params"]                     │
  └─────────────────────────────────────────────────────────────────────┘
```

## 2. EXACT INTEGRATION POINTS

### Point #1: `calculate_soc_target()` — BASE SOC TARGET (PRIMARY)

**File:** `/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner/calculations.py`
**Lines:** 209-243

```python
def calculate_soc_target(
    trip: Dict[str, Any],
    battery_capacity_kwh: float,
    consumption_kwh_per_km: float = 0.15,
    soc_buffer_percent: float = DEFAULT_SOC_BUFFER_PERCENT,
) -> float:
    # ... energy calculation ...
    energia_soc = (energia_kwh / battery_capacity_kwh) * 100
    soc_objetivo_base = energia_soc + soc_buffer_percent
    return soc_objetivo_base  # <-- LINE 243: Return value
```

**Current behavior:** Returns raw `energia_soc + buffer` without any cap.

**Integration:** Add a `dynamic_limit` parameter and apply `min(result, dynamic_limit)` before return.

**Callers (where this function is invoked):**
- `calculations.py:805` — inside `calculate_deficit_propagation()` loop
- `calculations.py:842` — in final result building loop
- `trip_manager.py:1287-1289` — `_calcular_soc_objetivo_base()` delegates to this
- `trip_manager.py:1955-1956` — `calcular_hitos_soc()` pre-computes soc_targets

### Point #2: `calculate_energy_needed()` — ENERGY CALCULATION

**File:** `calculations.py`
**Lines:** 307-377

```python
def calculate_energy_needed(
    trip, battery_capacity_kwh, soc_current, charging_power_kw,
    consumption_kwh_per_km, safety_margin_percent,
) -> Dict[str, Any]:
    # line 352: energia_objetivo = energia_viaje + energia_seguridad
    # line 355: energia_actual = (soc_current / 100.0) * battery_capacity_kwh
    # line 358: energia_necesaria = max(0.0, energia_objetivo - energia_actual)
```

**Integration:** If `soc_current` is capped by dynamic SOC, the `energia_actual` on line 355 should reflect the capped value. However, this function receives `soc_current` as a parameter — it is NOT the place to compute the cap. The cap must be applied at the CALLER level before passing `soc_current` to this function, OR the `soc_objetivo` (energia_objetivo) should be adjusted.

**Better approach:** Since the formula is `final_soc = min(required_soc, dynamic_limit)`, the cap belongs on the `soc_objetivo` computation (Point #1), not on `soc_current` (which is a read from the sensor).

### Point #3: `calculate_deficit_propagation()` — PROPAGATED TARGETS

**File:** `calculations.py`
**Lines:** 716-863

**Key lines:**
- **Line 803-805:** `soc_objetivo = soc_targets[original_idx]` or `calculate_soc_target(trip, battery_capacity_kwh)`
- **Line 808:** `soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]`
- **Line 840-842:** Second computation of `soc_objetivo`
- **Line 843:** `soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]`

**Integration:** After line 843, apply the dynamic cap:
```python
soc_objetivo_ajustado = min(soc_objetivo_ajustado, dynamic_limit)
```

This ensures backward-propagated deficits don't push SOC above the sweet spot.

### Point #4: `_populate_per_trip_cache_entry()` — PER-TRIP CHARGING DECISION

**File:** `emhass_adapter.py`
**Lines:** 542-740

**Key lines:**
- **Line 584-587:** `determine_charging_need()` call
- **Line 664-666:** `kwh_needed = decision.kwh_needed`, `total_hours = decision.def_total_hours`
- **Line 706-711:** `power_profile = self._calculate_power_profile_from_trips(...)`

**Integration:** The `determine_charging_need()` function at line 584 already uses SOC-aware energy calculation. If the dynamic cap reduces the required SOC, the resulting `kwh_needed` from `calculate_energy_needed()` would naturally be lower (since `energia_objetivo` = trip energy + safety margin, which stays the same, but the effective target SOC is lower).

The key insight: the dynamic cap reduces the **target** SOC, not the current SOC. So the energy needed to reach the target decreases. This means:
- `kwh_needed` from `determine_charging_need()` will be lower
- `total_hours` will be shorter
- `power_profile` will have fewer non-zero entries

### Point #5: `async_publish_all_deferrable_loads()` — BATCH SOC PROPAGATION

**File:** `emhass_adapter.py`
**Lines:** 781-1099

**Key lines:**
- **Line 993-1056:** Sequential SOC propagation between trips
- **Line 1054:** `projected_soc = projected_soc + soc_ganado - soc_consumido`

**Integration:** The `projected_soc` variable tracks the expected SOC after each trip's charging+consumption cycle. When the dynamic cap limits how much can be charged, `soc_ganado` (line 1043-1045) should reflect the reduced charging, and `projected_soc` will naturally be lower for subsequent trips.

## 3. CONFIG FLOW INTEGRATION PATTERN

### Pattern observed in `config_flow.py`

The codebase uses a **multi-step wizard** pattern:

```
Step 1: async_step_user() -> basic vehicle info
Step 2: async_step_sensors() -> battery, power, consumption, safety margin
Step 3: async_step_emhass() -> planning horizon, max deferrable loads
Step 4: async_step_presence() -> charging/home/plugged sensors
Step 5: async_step_notifications() -> notification service
```

Each step:
1. Defines a `vol.Schema` at module level (lines 51, 61, 83, 129, 160)
2. Has an `async_step_*()` method
3. Validates input with voluptuous constraints
4. Stores data in `self.context["vehicle_data"]` via `_get_vehicle_data()`
5. Calls the next step: `return await self.async_step_*()`

Options flow (`EVTripPlannerOptionsFlowHandler`, line 877) handles post-installation changes:
- Single step (`async_step_init`) with a compact schema
- Updates `entry.options`
- Triggers republish via `_handle_config_entry_update()`

### Where to add new config params

**For initial setup (add to Step 3 — EMHASS step):**
1. Add `CONF_*` constant in `const.py` (line ~38-40, near other EMHASS params)
2. Add `DEFAULT_*` constant in `const.py` (line ~66-69, near other defaults)
3. Import constants in `config_flow.py` (line ~28-44 import block)
4. Add field to `STEP_EMHASS_SCHEMA` (line 83-123)
5. Add validation in `async_step_emhass()` (line 393-542)

**For options flow (post-install changes):**
1. Add field to the options form schema (line 927-945)
2. Add to update_data dict (line 900-909)

**Recommended location for new constants:**
```
const.py, after line 40 (after CONF_INDEX_COOLDOWN_HOURS):
    CONF_SOC_CAP_ENABLED = "soc_cap_enabled"
    CONF_SOC_BASE = "soc_base"           # Default: 35
    CONF_SOC_PRESERVATION_FACTOR = "soc_preservation_factor"  # Default: 0.5
```

### How config flows into the adapter (`__init__.py`)

**File:** `__init__.py`
**Key lines:**
- **Line 141-146:** EMHASS adapter creation
  ```python
  if entry.data.get("planning_horizon_days") or entry.data.get("max_deferrable_loads"):
      emhass_adapter = EMHASSAdapter(hass, entry)
      await emhass_adapter.async_load()
      emhass_adapter.setup_config_entry_listener()
      trip_manager.set_emhass_adapter(emhass_adapter)
  ```

- **Line 133:** TripManager creation (no direct config injection; it reads from config_entries)

- **EMHASSAdapter.__init__** (emhass_adapter.py:57-140):
  ```python
  self._charging_power_kw = entry_data.get(CONF_CHARGING_POWER, 3.6)
  self._battery_capacity_kwh = entry_data.get(CONF_BATTERY_CAPACITY, 50.0)
  self._safety_margin_percent = entry_data.get("safety_margin_percent", DEFAULT_SAFETY_MARGIN)
  ```

**Integration path for new SOC cap config:**
1. Config entry stores params in `entry.data`
2. `EMHASSAdapter.__init__()` reads them from `entry_data`
3. `EMHASSAdapter` passes them to `calculations.py` functions as parameters
4. `calculations.py` functions use them in SOC target computation

## 4. RISK ASSESSMENT

### High Risk Areas

#### A. `calculate_deficit_propagation()` (calculations.py:716-863)

**Risk:** Modifying `soc_objetivo_ajustado` after deficit propagation could cause trips that previously needed charging to suddenly not need it, or vice versa if the cap causes cascading effects.

**Impact:** 
- Trips that rely on backward deficit propagation may get insufficient charge
- The backward propagation algorithm assumes targets are "what we need" — capping them changes the semantic meaning

**Mitigation:** The dynamic cap should be applied ONLY when `soc_objetivo_ajustado > dynamic_limit`, leaving lower targets unchanged. This preserves the deficit propagation behavior for trips that need SOC below the sweet spot.

#### B. `async_publish_all_deferrable_loads()` SOC propagation (emhass_adapter.py:993-1056)

**Risk:** The `projected_soc` variable drives SOC values for subsequent trips. If the dynamic cap reduces charging for trip N, `projected_soc` for trip N+1 will be lower, potentially causing trip N+1 to request more charge than before, creating a feedback loop.

**Impact:** Could cause unexpected behavior where later trips get more charging to compensate for earlier capped trips.

**Mitigation:** The dynamic cap on SOC targets naturally limits the maximum charge per trip. The propagation formula already handles this: `soc_ganado = min(def_total_hours, ventana_horas) * power / capacity * 100`. If `def_total_hours` is lower due to capped SOC, `soc_ganado` will be lower, and `projected_soc` will be lower — which is the correct behavior.

#### C. `calculate_power_profile_from_trips()` (calculations.py:953-1089)

**Risk:** This function produces the final power profile sent to EMHASS. If the dynamic cap is not applied consistently here, the power profile could request more energy than the SOC cap allows.

**Current behavior:** Lines 1032-1037 call `determine_charging_need()` which calls `calculate_energy_needed()`. Both use `soc_current` (from sensor), not `soc_target`. The energy needed is calculated as `target_energy - current_energy`.

**Impact:** If the cap is only applied in `calculate_soc_target()` but NOT in `calculate_energy_needed()`, the power profile will still request full energy (since `calculate_energy_needed` doesn't know about the cap).

**Mitigation:** The dynamic cap should be applied to the **target SOC**, which feeds into `energia_objetivo` in `calculate_energy_needed`. Specifically:
- `energia_objetivo = (capped_soc / 100) * battery_capacity_kwh + safety_margin_energy`
- This means the cap reduces the target, which reduces `energia_necesaria`, which reduces `power_profile` values.

### Medium Risk Areas

#### D. `determine_charging_need()` (calculations.py:260-304)

**Risk:** This is a pure function that decides whether and how much to charge. If it receives a `soc_current` from the sensor but the cap is applied to the `soc_objetivo`, the function needs to be aware of the cap to correctly compute `kwh_needed`.

**Current behavior:** Line 283-286 calls `calculate_energy_needed()` which computes `energia_objetivo = energia_viaje + energia_seguridad`. The SOC target is implicit (100% after trip). The cap should reduce this target.

**Mitigation:** Either modify `calculate_energy_needed()` to accept a `soc_target_cap` parameter, or compute the capped `energia_objetivo` before calling it.

#### E. Config migration for existing users

**Risk:** Adding new config params means existing users need a default value. If the default is `SOC_base=35` (aggressive cap), it could break users who are fine with charging to 100%.

**Mitigation:** Default `SOC_CAP_ENABLED` to `False` (disabled) for existing users. Only enable the cap when explicitly configured.

### Low Risk Areas

#### F. `__init__.py` — adapter wiring

**Risk:** Minimal. This is just data passing. Adding new config params to the adapter's `__init__` is a safe change.

**Impact:** No functional change to existing behavior.

#### G. `trip_manager.py` — trip lifecycle

**Risk:** Minimal. The TripManager doesn't directly compute SOC targets — it delegates to `calculations.py` and `EMHASSAdapter`. As long as the delegation remains the same, trip lifecycle is unaffected.

#### H. `config_flow.py` — form validation

**Risk:** Minimal. Adding new form fields is standard. Must ensure validation ranges are sensible (e.g., `soc_base` between 0 and 100, `preservation_factor` between 0 and 1).

## 5. SUMMARY OF INTEGRATION POINTS

| # | Location | File | Lines | Change |
|---|----------|------|-------|--------|
| 1 | `calculate_soc_target()` | calculations.py | 209-243 | Add `dynamic_limit` param, apply `min(result, dynamic_limit)` |
| 2 | `calculate_deficit_propagation()` | calculations.py | 716-863 | Apply cap to `soc_objetivo_ajustado` at line 843 |
| 3 | `_populate_per_trip_cache_entry()` | emhass_adapter.py | 542-740 | Pass dynamic_limit to charging decision |
| 4 | `async_publish_all_deferrable_loads()` | emhass_adapter.py | 781-1099 | Pass dynamic_limit to SOC propagation |
| 5 | `const.py` | const.py | ~line 40 | Add CONF_SOC_CAP_ENABLED, CONF_SOC_BASE, CONF_SOC_PRESERVATION_FACTOR |
| 6 | `config_flow.py` | config_flow.py | ~line 83-123, ~line 927-945 | Add fields to EMHASS step and options form |
| 7 | `EMHASSAdapter.__init__()` | emhass_adapter.py | 57-140 | Read new config params from entry_data |

## 6. DATAFLOW SUMMARY: SOC TO POWER PROFILE

```
soc_sensor (Home Assistant entity)
    |
    v
EMHASSAdapter._get_current_soc() -> float (e.g., 65.0)
    |
    v (used as soc_current in determine_charging_need / calculate_energy_needed)
    |
    +--> SOC_BASE constant (default 35.0) ---+
    |                                         |
    +--> T_user config (hours) -------------->|
    |                                         |
    +---> preservation_factor --------------->|---> dynamic_limit
                                              |       = SOC_base + (100 - SOC_base) * h / (h + T_adjusted)
    +---> SOC_target (raw, from trip) ------->|---> final_soc = min(SOC_target, dynamic_limit)
                                              |
    v
calculate_energy_needed(final_soc) -> kwh_needed
    |
    v
determine_charging_need() -> ChargingDecision
    |
    v
_calculate_power_profile_from_trips() -> List[float] (watts per hour)
    |
    v
_cached_power_profile -> coordinator.data -> EMHASS sensor
```

The critical observation: the dynamic cap affects the **target** SOC, not the **current** SOC. The current SOC is a sensor reading (user's actual battery level). The target SOC is what the planner wants to achieve by the trip deadline. The dynamic cap limits how high the target can go, which reduces `kwh_needed`, which reduces charging hours, which produces a shorter power profile.
