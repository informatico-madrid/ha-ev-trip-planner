# Design: Dynamic SOC Capping

## Overview

Add a degradation-aware SOC cap algorithm that limits battery charging to a continuous upper bound calculated from idle time and projected post-trip SOC. Integrate as `min(required, dynamic_limit)` inside `calculate_deficit_propagation()`. Extract a `BatteryCapacity` abstraction that always uses real capacity (nominal x SOH) as the single source of truth.

## Architecture

```mermaid
graph TB
    subgraph Config["Config Flow / Options Flow"]
        A1[T_base slider 6-48h]
        A2[SOH sensor selector]
    end

    subgraph Core["calculations.py"]
        B1[BatteryCapacity class]
        B2[calculate_dynamic_soc_limit()]
        B3[calculate_deficit_propagation]
    end

    subgraph Orchestration["trip_manager.py"]
        C1[calcular_hitos_soc]
        C2[async_calcular_energia_necesaria]
    end

    subgraph Publishing["emhass_adapter.py"]
        D1[_populate_per_trip_cache_entry]
        D2[_calculate_power_profile_from_trips]
    end

    A1 -->|t_base| B2
    A2 -->|soh_sensor_id| B1

    B2 -->|dynamic_limit| B3
    B1 -->|real_capacity| B3
    B1 -->|real_capacity| C1
    B1 -->|real_capacity| C2
    B1 -->|real_capacity| D1
    B1 -->|real_capacity| D2

    C1 -->|capped SOC targets| D1
    C2 -->|real_capacity energy| D1
```

## Components

### Component 1: `BatteryCapacity`

**Purpose**: Single source of truth for real battery capacity. Encapsulates nominal capacity and optional SOH sensor lookup.

**Responsibilities**:
- Return `real_capacity` = `nominal_capacity * SOH_value / 100`
- Fallback to nominal when SOH sensor not configured or unavailable
- Debounce SOH sensor reads (sensor values can be noisy)

**Interfaces**:

```python
@dataclass
class BatteryCapacity:
    nominal_capacity_kwh: float
    soh_sensor_entity_id: str | None = None
    _soh_value: float | None = None       # cached SOH value
    _soh_cached_at: datetime | None = None # when SOH was last read
    fallback_capacity: float = 50.0
    SOH_CACHE_TTL_SECONDS: int = 300       # 5-minute cache expiration

    def get_capacity(self, hass: Any | None = None) -> float:
        """Real capacity in kWh with time-based cache expiration.

        If SOH sensor is configured and cache is stale (>5 min), re-read the
        sensor. If the sensor is unavailable, keep the last valid cached value
        (hysteresis — do not oscillate capacity when sensor is noisy).
        """
        if not hass or not self.soh_sensor_entity_id:
            return self.nominal_capacity_kwh

        # Re-read if cache is stale OR never initialized
        should_read = (
            self._soh_cached_at is None
            or (datetime.now() - self._soh_cached_at).total_seconds() > self.SOH_CACHE_TTL_SECONDS
        )
        if should_read:
            new_val = self._read_soh(hass)
            if new_val is not None:
                self._soh_value = new_val  # updated from sensor
                self._soh_cached_at = datetime.now()
            # If new_val is None, keep old cached value (hysteresis)

        return self._compute_capacity()

    def get_capacity_kwh(self, hass: Any | None = None) -> float:
        """Alias for get_capacity (backward compat with battery_capacity_kwh)."""
        return self.get_capacity(hass)

    def _read_soh(self, hass: Any) -> float | None:
        """Read current SOH sensor value. Returns None if unavailable."""
        state = hass.states.get(self.soh_sensor_entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            val = float(state.state)
            return max(10.0, min(100.0, val))  # clamp to valid range
        except (ValueError, TypeError):
            return None

    def _compute_capacity(self) -> float:
        """Compute capacity from cached SOH value."""
        if self._soh_value is not None:
            return self.nominal_capacity_kwh * self._soh_value / 100.0
        return self.nominal_capacity_kwh  # fallback to nominal
```

**Where used**: `calculations.py`, `emhass_adapter.py`, `trip_manager.py`

**Error handling**:
- SOH sensor not configured → use nominal (no crash)
- SOH sensor unavailable (`unknown`/`unavailable`) → use nominal (no crash)
- SOH value outside [10, 100] → clamp and log warning

---

### Component 2: `calculate_dynamic_soc_limit()`

**Purpose**: Pure algorithm that computes SOC upper bound from idle hours, post-trip SOC, and battery parameters.

**Location**: `calculations.py` (end of file, before deferrable parameters section)

**Signature**:

```python
def calculate_dynamic_soc_limit(
    t_hours: float,              # idle hours until next charging opportunity
    soc_post_trip: float,        # projected SOC % after trip completes
    battery_capacity_kwh: float, # battery capacity in kWh (real, not nominal)
    t_base: float = 24.0,        # user-configurable (default 24h, range 6-48h)
    soc_base: float = 35.0,      # hardcoded sweet spot
) -> float:
    """Compute degradation-aware SOC upper bound.

    Args:
        t_hours: Idle hours between trip N completion and next charging opportunity.
        soc_post_trip: Projected SOC % after the current trip completes.
        battery_capacity_kwh: Real battery capacity (already SOH-adjusted).
        t_base: User-configurable time parameter controlling cap aggressiveness.
        soc_base: Hardcoded battery chemistry sweet spot (35% for NMC/NCA).

    Returns:
        SOC limit percentage [35.0, 100.0].
    """
    risk = t_hours * (soc_post_trip - soc_base) / (100.0 - soc_base)
    if risk <= 0:
        return 100.0
    limit = soc_base + (100.0 - soc_base) * (1.0 / (1.0 + risk / t_base))
    # Clamp to [soc_base, 100.0]
    return max(soc_base, min(100.0, limit))
```

**Responsibilities**:
- Pure function: no I/O, no state, fully deterministic
- Exported via `__all__` in calculations.py
- Returns 100.0 when risk <= 0 (no capping active)
- Clamps result to [35.0, 100.0]

---

### Component 3: Deficit Propagation Integration

**Purpose**: Apply the dynamic SOC cap inside `calculate_deficit_propagation()` in BOTH loops.

**Integration point**: `calculations.py:calculate_deficit_propagation()`

**Changes to existing function signature**:

```python
def calculate_deficit_propagation(
    trips: List[Dict[str, Any]],
    soc_data: List[Dict[str, Any]],
    windows: List[Dict[str, Any]],
    tasa_carga_soc: float,
    battery_capacity_kwh: float,
    reference_dt: datetime,
    trip_times: Optional[List[Optional[datetime]]] = None,
    soc_targets: Optional[List[float]] = None,
    t_base: float = 24.0,          # NEW: threaded from config
    soc_caps: Optional[List[float]] = None,  # NEW: pre-computed caps per trip
) -> List[Dict[str, Any]]:
```

**Backward loop (lines ~786-824) — change**:

After computing `soc_objetivo_ajustado` at line ~808, insert cap:

```python
# Line ~808: after soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]
# NEW: apply dynamic SOC cap
if soc_caps and original_idx < len(soc_caps):
    dynamic_limit = soc_caps[original_idx]
    soc_objetivo_final = min(soc_objetivo_ajustado, dynamic_limit)
else:
    soc_objetivo_final = soc_objetivo_ajustado  # backward compat: no cap

# Continue with deficit calculation using soc_objetivo_final
capacidad_carga = tasa_carga_soc * ventana_horas
if soc_inicio + capacidad_carga < soc_objetivo_final:
    deficit = soc_objetivo_final - (soc_inicio + capacidad_carga)
    # ... propagate deficit to previous trip
```

**Key invariant**: deficit is computed from the CAPPED target, not the uncapped one. This prevents artificial deficits from propagating backward when capping restricts charging.

**Forward loop (lines ~828-861) — change**:

Recompute `soc_objetivo_ajustado` and apply cap again:

```python
# Line ~843: after soc_objetivo_ajustado recomputation
if soc_caps and original_idx < len(soc_caps):
    dynamic_limit = soc_caps[original_idx]
    soc_objetivo_final = min(soc_objetivo_ajustado, dynamic_limit)
else:
    soc_objetivo_final = soc_objetivo_ajustado

# Result uses soc_objetivo_final
results.append({
    "trip_id": trip.get("id", f"trip_{original_idx}"),
    "soc_objetivo": round(soc_objetivo_final, 2),  # was: soc_objetivo_ajustado
    "kwh_necesarios": round(max(0.0, (soc_objetivo_final - soc_inicio) * battery_capacity_kwh / 100), 3),
    # ...
})
```

---

### Component 4: Forward Propagation of Capped SOC

**Purpose**: The SOC after each trip (used as start SOC for the next trip) must use the CAPPED `soc_objetivo_final`, not the uncapped `soc_objetivo_ajustado`.

**Where**: `trip_manager.py:calcular_hitos_soc()` — after calling `calculate_deficit_propagation()`.

The existing forward propagation in the SOC milestone calculation already uses sequential SOC projection. The change is:
- Current: `soc_actual` advances by `soc_llegada` from `calcular_soc_inicio_trips`
- After capping: the forward SOC for trip N+1 = capped `soc_objetivo` from trip N

**Implementation**: After `calculate_deficit_propagation()` returns, extract the capped `soc_objetivo` from each result and use it as the forward-propagated SOC when building subsequent charging windows.

---

### Component 5: T_base Config

**Purpose**: User-configurable slider in the options flow.

**Where**: `config_flow.py` — both initial setup AND options flow.

**Initial flow (STEP_SENSORS_SCHEMA, line 61)**: Add T_base slider to the sensors step, in a new "Battery Health" section.

```python
STEP_SENSORS_SCHEMA = vol.Schema(
    {
        # ... existing fields ...
        vol.Optional(
            CONF_T_BASE,
            default=24.0,
            description="T_base (6-48h, default 24h)",
        ): vol.All(vol.Coerce(float), vol.Range(min=6.0, max=48.0)),
        vol.Optional(CONF_SOH_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", multiple=False),
        ),
    }
)
```

**Options flow (EVTripPlannerOptionsFlowHandler)**: Add T_base and SOH to the options form:

```python
data_schema = vol.Schema({
    vol.Required(CONF_BATTERY_CAPACITY, default=current_battery): ...,
    vol.Required(CONF_CHARGING_POWER, default=current_charging): ...,
    vol.Required(CONF_CONSUMPTION, default=current_consumption): ...,
    vol.Required(CONF_SAFETY_MARGIN, default=current_safety): ...,
    vol.Optional(CONF_T_BASE, default=current_t_base): vol.All(vol.Coerce(float), vol.Range(min=6.0, max=48.0)),
    vol.Optional(CONF_SOH_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", multiple=False),
    ),
})
```

**Validation**:
- T_base: 6.0-48.0, rejects outside range with `vol.Range`
- SOH: validated at runtime when reading sensor value (10-100%)

---

### Component 6: EMHASS Adapter

**Purpose**: Use capped SOC + real capacity in `_populate_per_trip_cache_entry()`.

**Where**: `emhass_adapter.py:_populate_per_trip_cache_entry()`

**Changes**:

1. `_populate_per_trip_cache_entry()` already receives `battery_capacity_kwh` parameter. This will now be `real_capacity` (from `BatteryCapacity.get_capacity()`).

2. Charging decision already uses `determine_charging_need()` which uses `battery_capacity_kwh`. Since the SOC targets passed in are now capped, the `kwh_needed` automatically reflects capping.

3. `P_deferrable_nom` computation:
```python
# CRITICAL: P_deferrable_nom is ALWAYS the fixed charger power from config flow.
# It does NOT change with SOC capping. The SOC cap reduces kwh_needed,
# which reduces def_total_hours = kwh_needed / charger_power.
# Example: if charging_power_kw = 11, P_deferrable_nom is always 11000W.
# When SOC cap reduces kwh_needed from 11kWh to 5.5kWh:
#   - P_deferrable_nom stays at 11000W (hardware is fixed)
#   - def_total_hours goes from 1.0h to 0.5h

"P_deferrable_nom": round(power_watts, 0) if has_charging else 0.0,
# power_watts comes from determine_charging_need() which sets:
#   power_watts = charging_power_kw * 1000 (FIXED charger power)
# This value MUST NOT be multiplied by cap_ratio.
```

4. `_calculate_power_profile_from_trips()` delegates to `calculate_power_profile_from_trips()` which receives `battery_capacity_kwh`. This parameter will be `real_capacity`.

5. The power_profile array uses fixed charger power during charging windows, 0W outside. The SOC cap affects WHICH windows are active (via reduced start/end timesteps), NOT the power values within windows.

---

### Component 7: Trip Manager Wiring

**Purpose**: Thread `t_base` and `BatteryCapacity` through `calcular_hitos_soc()`.

**Where**: `trip_manager.py:calcular_hitos_soc()`

**Changes**:

```python
async def calcular_hitos_soc(
    self,
    trips: List[Dict[str, Any]],
    soc_inicial: float,
    charging_power_kw: float,
    vehicle_config: Optional[Dict[str, Any]] = None,
    hora_regreso: Optional[datetime] = None,
    battery_capacity: Optional[BatteryCapacity] = None,  # NEW
    t_base: float = 24.0,  # NEW
) -> List[Dict[str, Any]]:
```

After computing results from `calculate_deficit_propagation()`, compute `soc_caps` per trip and pass them to the function. Also use capped SOC for forward propagation.

### Component 7b: `async_generate_power_profile()` Entry Point Threading

**Purpose**: The public API entry point `async_generate_power_profile()` must receive `t_base` and `BatteryCapacity` and pass them through to `calcular_hitos_soc()`.

**Where**: `trip_manager.py:async_generate_power_profile()` (line ~1974)

This function calls `calcular_hitos_soc()` internally (line ~1959). The design adds `t_base` and `battery_capacity` as optional parameters with defaults, ensuring backward compatibility:

```python
async def async_generate_power_profile(
    self,
    trips: List[Dict[str, Any]],
    soc_inicial: float,
    charging_power_kw: float,
    vehicle_config: Optional[Dict[str, Any]] = None,
    hora_regreso: Optional[datetime] = None,
    battery_capacity: Optional[BatteryCapacity] = None,  # NEW: optional
    t_base: float = 24.0,  # NEW: optional, default matches algorithm default
) -> Dict[str, Any]:
    # ... existing logic ...
    hits = await self.calcular_hitos_soc(
        trips, soc_inicial, charging_power_kw,
        vehicle_config=vehicle_config,
        hora_regreso=hora_regreso,
        battery_capacity=battery_capacity,  # NEW: thread through
        t_base=t_base,  # NEW: thread through
    )
    # ... rest of logic uses hits with capped SOC targets ...
```

**Caller wiring**: The caller (typically `emhass_adapter.py` or the Home Assistant platform) passes `t_base` and `BatteryCapacity` from `config_entry.data` / `config_entry.options`. If not configured, defaults are used (backward compatible).

---

## Data Flow

```mermaid
sequenceDiagram
    participant Config
    participant TM as TripManager
    participant Calc as calculations.py
    participant EMH as EMHASSAdapter
    participant SOH as SOH Sensor

    Config->>Config: User sets T_base (6-48h)
    Config->>Config: User selects SOH sensor entity
    Config->>Calc: BatteryCapacity(nominal, soh_entity)

    TM->>Calc: calcular_hitos_soc(trips, soc_inicial, ...)
    Calc->>Calc: BatteryCapacity.get_capacity() -> real_capacity
    Calc->>Calc: SOH value from entity (or nominal fallback)

    Calc->>Calc: calculate_deficit_propagation(
        trips, soc_data, windows, tasa_carga,
        battery_capacity=real_capacity,
        t_base=t_base,
        soc_caps=[precomputed_per_trip]
    )

    Calc->>Calc: Backward loop: cap soc_objetivo_final
    Calc->>Calc: Forward loop: cap soc_objetivo_final

    TM->>EMH: _populate_per_trip_cache_entry(
        battery_capacity_kwh=real_capacity,
        soc_current=capped_soc_from_propagation
    )

    EMH->>EMH: determine_charging_need() uses capped SOC
    EMH->>EMH: power_profile uses real_capacity
    EMH->>EMH: 168-element power profile with capped targets
```

## Technical Decisions

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Where to apply cap | Inside deficit propagation vs. after results | Inside (both loops) | FR-2 requires cap before deficit calculation; prevents artificial backward propagation |
| SOH integration | New class vs. inline math | `BatteryCapacity` class (FR-8) | SOLID: single source of truth; eliminates duplicated capacity math across files |
| T_base config location | Sensors step vs. dedicated step vs. options only | Both sensors AND options step | Matches existing pattern (battery_capacity in sensors step); options flow allows changes without re-adding vehicle |
| SOH sensor fallback | Strict fail vs. graceful fallback | Graceful (use nominal) | NFR-7: no crash when sensor unavailable |
| soc_base | User-configurable vs. hardcoded | Hardcoded 35.0 | FR-1.4: 35% is the chemistry sweet spot; not a user decision |
| Forward propagation source | Uncapped soc_objetivo_ajustado vs. capped soc_objetivo_final | Capped | FR-9: forward SOC must be consistent with capped targets |
| SOH sensor read timing | During calculation vs. pre-resolved at config | Pre-resolved at construction | Avoids sensor I/O in calculation path; keeps calculations.py pure |
| Config flow structure | New health step vs. add to sensors step | Add to sensors step | Minimal UI change; health mode is always on (no toggle needed) |
| SOH debouncing | Real-time vs. averaged vs. cached | Cached at construction | Sensor updates frequently; use value at config read time |

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `custom_components/ev_trip_planner/const.py` | Modify | Add `CONF_T_BASE`, `CONF_SOH_SENSOR`, defaults, ranges |
| `custom_components/ev_trip_planner/calculations.py` | Modify | Add `BatteryCapacity` class, `calculate_dynamic_soc_limit()`, modify `calculate_deficit_propagation()` |
| `custom_components/ev_trip_planner/config_flow.py` | Modify | Add T_base slider + SOH sensor to sensors step; add to options flow |
| `custom_components/ev_trip_planner/trip_manager.py` | Modify | Thread `BatteryCapacity` and `t_base` through `calcular_hitos_soc()` |
| `custom_components/ev_trip_planner/emhass_adapter.py` | Modify | Use `real_capacity` in `_populate_per_trip_cache_entry()` and `_calculate_power_profile_from_trips()` |
| `tests/test_dynamic_soc_capping.py` | Create | 5 unit tests: algorithm accuracy, T_base variability, edge cases, SOC cap integration, SOH fallback |

## Migration Strategy

**Purpose**: Existing installations must continue working without manual intervention. New keys are added with safe defaults.

**Current state**: `CONFIG_VERSION` is 2 (needs to be bumped to 3).

**Migration steps**:

```python
# config_flow.py — entry migration
async def async_migrate_entry(hass, config_entry):
    """Migrate old config entry to include new battery health fields."""
    if config_entry.version > 3:
        return True

    if config_entry.version == 2:
        data = dict(config_entry.data)
        data[CONF_T_BASE] = DEFAULT_T_BASE  # 24.0 — algorithm default
        data[CONF_SOH_SENSOR] = ""  # empty string = not configured
        config_entry.version = 3
        hass.config_entries.async_update_entry(config_entry, data=data)

    return True
```

**Read pattern** (every place reading config):
```python
# Safe reads with defaults — never KeyError
t_base = config_entry.data.get(CONF_T_BASE, DEFAULT_T_BASE)
soh_sensor = config_entry.data.get(CONF_SOH_SENSOR, "") or config_entry.options.get(CONF_SOH_SENSOR, "")
```

**Options flow**: The options flow writes to `config_entry.options`. The initial flow writes to `config_entry.data`. Both paths must be consulted:
```python
def get_config_value(self, key: str, default):
    """Check options first (user modifications), then data (initial install)."""
    return self.config_entry.options.get(key, self.config_entry.data.get(key, default))
```

**Backward compatibility guarantees**:
- Existing installs without `CONF_T_BASE` → use `DEFAULT_T_BASE` (24.0) → algorithm works identically to pre-m403 for typical scenarios
- Existing installs without `CONF_SOH_SENSOR` → `BatteryCapacity.get_capacity()` returns nominal capacity → identical behavior
- No breaking changes to any function signatures — all new parameters are optional with defaults
- `CONFIG_VERSION` bump ensures migration runs once per install

| Error Scenario | Handling Strategy | User Impact |
|----------------|-------------------|-------------|
| SOH sensor not configured | Use nominal capacity | No visible change (default behavior) |
| SOH sensor unavailable (`unknown`) | Use nominal capacity | No visible change |
| SOH sensor value < 10% | Clamp to 10%, log warning | Very conservative capacity estimate |
| SOH sensor value > 100% | Clamp to 100%, log warning | Nominal capacity used |
| T_base outside 6-48h | Config flow validation rejects | User sees validation error on config form |
| SOH sensor returns non-numeric | Log warning, fallback to nominal | No crash |
| `calculate_dynamic_soc_limit()` returns < 35 | Clamp to 35 | Minimum SOC always valid |
| `calculate_dynamic_soc_limit()` returns > 100 | Clamp to 100 | No over-charging |

## Edge Cases

- **Zero idle hours** (t_hours=0): risk=0, limit=100.0 (no capping). Handled explicitly in formula.
- **soc_post_trip <= 35%**: risk <= 0, limit = 100.0 (large trip scenario). Handled by `risk <= 0` guard.
- **SOC target already below dynamic limit**: cap has no effect (min preserves lower value).
- **Multiple identical trips** (Scenario C): each trip gets its own cap based on its own idle hours and post-trip SOC.
- **SOH sensor entity deleted after config**: HA entity state returns `unavailable` → fallback to nominal.
- **T_base=6 (max aggressiveness)**: tightest cap; large trips still get 100% via negative risk path.
- **T_base=48 (max conservatism)**: loosest cap; may barely differ from 100%.
- **Capacity = 0**: `calculate_charging_rate` already returns 0.0 for this case; `BatteryCapacity.get_capacity()` clamps to fallback.

## Test Strategy

### Test Double Policy

| Type | What it does | When to use |
|---|---|---|
| **Stub** | Returns predefined data, no behavior | Isolate SUT from HA I/O; only SUT's return value matters |
| **Fake** | Simplified real implementation | Integration tests needing real behavior without real infrastructure |
| **Mock** | Verifies interactions (call args, call count) | Only when the interaction itself is the observable outcome |
| **Fixture** | Predefined data state, not code | Any test that needs known initial data |

Own wrapper ≠ external dependency. If you wrote it, test it real.

### Mock Boundary

| Component (from this design) | Unit test | Integration test | Rationale |
|---|---|---|---|
| `BatteryCapacity.get_capacity()` | Stub SOH sensor | Real (no external I/O) | Own logic, deterministic |
| `calculate_dynamic_soc_limit()` | None | None | Pure function, no doubles needed |
| `calculate_deficit_propagation()` (capped) | Stub windows, soc_data, soc_caps | Real (with mock trip_times) | Business logic, test with real inputs |
| TripManager `calcular_hitos_soc()` | Mock `_get_trip_time`, `calcular_soc_inicio_trips` | Mock `_get_trip_time` only | HA-dependent orchestration |
| `EMHASSAdapter._populate_per_trip_cache_entry()` | Mock `async_assign_index_to_trip`, `determine_charging_need` | Real adapter logic with stubs | HA I/O boundaries |

### Fixtures & Test Data

| Component | Required state | Form |
|---|---|---|
| `calculate_dynamic_soc_limit()` | Scenarios A, B, C inputs (t_hours, soc_post_trip, battery_capacity) | Inline constants / `@pytest.mark.parametrize` |
| `BatteryCapacity` | Nominal=60.0, SOH=90% → expected real_capacity=54.0 | Factory `build_battery_capacity(nominal, soh_value)` |
| `calculate_deficit_propagation()` (capped) | 3 trips with known soc_targets, windows, deficit propagation chain | Fixture `sample_trips_with_caps()` returning (trips, soc_data, windows, soc_caps) |
| Config flow T_base | Default=24.0, min=6.0, max=48.0, invalid=3.0 | Inline constants |
| EMHASS adapter | Capped SOC targets, real_capacity=54.0 | Fixture `capped_trip_params(real_capacity=54.0)` |

### Test Coverage Table

| Component / Function | Test type | What to assert | Test double |
|---|---|---|---|
| `calculate_dynamic_soc_limit(22, 41, 30, t_base=24)` | unit | Returns 94.9 (±1) | none |
| `calculate_dynamic_soc_limit(22, 41, 30, t_base=24)` repeated 4x | unit | Same limit 94.9 each iteration (Scenario C) | none |
| `calculate_dynamic_soc_limit(t, 0, 60)` | unit | Returns 100.0 (negative risk) | none |
| `calculate_dynamic_soc_limit(0, 80, 60)` | unit | Returns 100.0 (zero idle hours) | none |
| `calculate_dynamic_soc_limit` with t_base=6 | unit | Tighter cap than t_base=24 (e.g., 87 vs 95) | none |
| `BatteryCapacity.get_capacity()` nominal only | unit | Returns nominal (60.0) when SOH not configured | none |
| `BatteryCapacity.get_capacity()` with SOH=90% | unit | Returns 54.0 (60*0.9) | none |
| `BatteryCapacity.get_capacity()` SOH unavailable | unit | Returns nominal fallback (60.0) | Stub SOH returns None |
| `calculate_deficit_propagation()` with capped soc | unit | Capped trip SOC <= dynamic_limit | Stub windows/soc_data, inject soc_caps |
| `calculate_deficit_propagation()` without caps | unit | Result matches existing (uncapped) behavior | Stub windows/soc_data, no soc_caps |
| Config flow: T_base slider accepts 24.0 | unit | Persisted in options | None (volition validation) |
| Config flow: T_base=3.0 rejected | unit | Form error shown | Stub entity registry |
| Config flow: SOH sensor selector shows sensors | unit | Entity selector with domain="sensor" | Stub entity registry |
| EMHASS adapter uses capped SOC | integration | `def_total_hours` computed from capped SOC | Mock `async_assign_index_to_trip` |
| EMHASS adapter uses real_capacity | integration | `P_deferrable_nom` reflects real_capacity (not nominal) | Mock index assignment |

### Test File Conventions

- **Test runner**: pytest (`python -m pytest`)
- **Test file location**: `tests/test_*.py` (flat directory)
- **Integration test pattern**: `test_*.py` with `@pytest.mark.asyncio`
- **Mock cleanup**: `pytest` auto-cleans `unittest.mock` mocks; use `MagicMock(return_value=X)` pattern
- **Fixture/factory location**: `tests/conftest.py` for shared fixtures; inline for test-specific data
- **Async mode**: `auto` (pyproject.toml: `asyncio_mode = "auto"`)

### ABSOLUTE PRIORITIES: Zero Regressions + 100% Coverage + E2E

**1. Zero Regressions — Non-Negotiable**

Before ANY code change, verify ALL existing test files pass:
```bash
# Run ALL existing tests — MUST pass before touching any code
python -m pytest tests/ -v
# Must include: test_soc_milestone.py, test_power_profile_positions.py,
# test_soc_100_deficit_propagation_bug.py, and EVERY other test file
```

After each logical group of changes, re-run the full suite:
- After `const.py` changes → full suite
- After `calculations.py` changes → full suite
- After `config_flow.py` changes → full suite
- After `trip_manager.py` changes → full suite
- After `emhass_adapter.py` changes → full suite
- At the END → full suite

If ANY existing test fails, STOP. Analyze the failure before proceeding.

**2. 100% Test Coverage — Absolute Priority**

- `fail_under = 100` in pyproject.toml must remain true
- New code must achieve 100% coverage
- No `# pragma: no cover` comments allowed
- Coverage must be measured on ALL files touched: `const.py`, `calculations.py`, `config_flow.py`, `trip_manager.py`, `emhass_adapter.py`

**3. E2E Test Execution — After Each Few Steps**

After completing every 3 implementation tasks (or any logical grouping), execute e2e tests:
```bash
# Run e2e tests to validate the feature end-to-end
python -m pytest tests/e2e/ -v --tb=short
```

If any e2e test fails:
1. STOP implementation
2. Analyze the root cause
3. Fix the issue (code or test)
4. Verify the fix doesn't regress other tests
5. Resume implementation

**4. Test Maintenance — Manage Outdated Tests**

If a change legitimately makes an existing test invalid (e.g., expected output changed due to the new algorithm):
1. Document WHY the test is changing
2. Update the test assertion to match the new correct behavior
3. Add a comment explaining the old vs new expected value
4. Verify no OTHER tests are affected

Common outdated test patterns to watch for:
- `test_soc_milestone.py`: may need assertions updated for capped SOC targets
- `test_power_profile_positions.py`: may need power profile expectations updated
- `test_soc_100_deficit_propagation_bug.py`: may need SOC 100% expectations updated

### Test Strategy — Coverage Verification Gate

Before marking the feature as complete, the following MUST all pass:
- [ ] All existing tests pass (zero regressions)
- [ ] New tests pass (5 unit tests in test_dynamic_soc_capping.py)
- [ ] 100% coverage on all modified files
- [ ] All e2e tests pass
- [ ] mypy type checking passes (zero errors)
- [ ] Linting passes (zero warnings)

## Performance Considerations

- `calculate_dynamic_soc_limit()`: single formula evaluation, < 1ms per trip (NFR-5)
- `BatteryCapacity.get_capacity()`: arithmetic operation, O(1), no I/O
- SOH sensor read: pre-resolved at construction (no repeated sensor I/O in hot path)
- Deficit propagation: unchanged algorithmic complexity; O(n) backward + O(n) forward = same as before
- Config flow: one-time sensor lookup at config time, not during operation

## Security Considerations

- SOH sensor entity validation: only accept `sensor` domain entities (via EntitySelector in config flow)
- SOH value clamping: reject values outside [10, 100] at config time (vol.Range) and clamp at runtime
- No user-facing configuration of `soc_base` (hardcoded 35.0) prevents unsafe chemistry settings
- Config flow uses `voluptuous` schema validation (existing pattern)

## Existing Patterns to Follow

- **Pure functions in calculations.py**: All calculation logic extracted from HA-dependent code; testable with `@pytest.mark.parametrize` and no mocks
- **datetime.now() replaced by reference_dt**: Pure functions take explicit `reference_dt` parameter for deterministic testing (already established in calculations.py)
- **MagicMock for helper methods**: Tests mock `TripManager._get_trip_time`, `calcular_soc_inicio_trips`, etc. with `MagicMock(return_value=X)`
- **Voluptuous schemas**: Config flow uses `vol.Schema` with `vol.Required`, `vol.Optional`, `vol.All`, `vol.Range`
- **EntitySelector for sensor config**: SOH sensor follows existing pattern (CONF_SOC_SENSOR at line 73 of config_flow.py)
- **DataUpdateCoordinator pattern**: Coordinator exposes data via `coordinator.data`; tests access through this interface
