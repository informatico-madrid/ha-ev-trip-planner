# 🚀 Milestone 4: Smart Charging Profile — Technical Documentation

**Implementation Document**
**Version**: 1.0
**Date**: 2025-12-14
**Status**: ✅ IMPLEMENTED & VALIDATED (historical — completed in v0.4.0-dev, current version is v0.5.20)
**Target**: v0.4.0-dev

---

## 📋 Executive Summary

Milestone 4 implements **Smart Charging Profile**, a functionality that automatically calculates when and how much to charge the electric vehicle based on:
- **Current SOC** (State of Charge) of the vehicle
- **Energy needed** for scheduled trips
- **Safety margin** of 40% minimum post-trip SOC
- **Hours available** before each trip

**Result**: The system generates a binary power profile (0W or maximum power) that intelligently distributes charging, avoiding critical batteries and optimizing charger usage.

---

## 🎯 Implemented Features

### 1. Necessary Energy Calculation (`async_calcular_energia_necesaria`)

**File**: `custom_components/ev_trip_planner/trip_manager.py` (lines 660-748)

```python
async def async_calcular_energia_necesaria(
    self, 
    trip: Dict[str, Any], 
    vehicle_config: Dict[str, Any]
) -> Dict[str, Any]:
```

**Calculation Logic**:
1. **Gets current SOC** of the vehicle from configured sensor
2. **Calculates current energy** in battery: `energia_actual_kwh = (soc_actual / 100) * capacidad_bateria_kwh`
3. **Calculates trip energy**: `energia_viaje` (directly from `kwh` or from `km * consumo`)
4. **Calculates necessary energy (gross)**: `energia_necesaria = max(0, energia_viaje - energia_actual)`
5. **Applies safety margin**: `energia_final = energia_necesaria * (1 + safety_margin_percent / 100)`
   - `safety_margin_percent` is configurable (0-50%, default 10%)
   - Applied to charging deficit, not arrival reserve
6. **Calculates charging hours**: `horas_carga = energia_final / potencia_carga_kw`

**Returns**:
```python
{
    "energia_necesaria_kwh": float,        # kWh to charge (includes margin)
    "horas_carga_necesarias": float,       # Hours needed to charge
    "horas_disponibles": float,            # Hours until trip
    "margen_seguridad_aplicado": float,    # Margin percentage used
}
```
⚠️ **NOTE**: `alerta_tiempo_insuficiente` is returned by `async_calcular_energia_necesaria()` but is **NOT exposed** to users via sensors or notifications. The user-facing `calcular_ventana_carga()` returns `es_suficiente` instead.

**Example with Chispitas** (safety_margin=10%):
- Current SOC: 49% → 19.6 kWh available
- Trip: 50 km → 7.5 kWh needed
- Energy needed raw: `max(0, 7.5 - 19.6) = 0` → 0 kWh (already has enough)
- **With 10% margin**: still 0 kWh
- **Charging hours**: 0 hours

---

### 2. Power Profile Generation (`async_generate_power_profile`)

**File**: `custom_components/ev_trip_planner/trip_manager.py` (lines 750-890)

```python
async def async_generate_power_profile(
    self,
    charging_power_kw: float,
    planning_horizon_days: int = 7,
    vehicle_config: Optional[Dict[str, Any]] = None
) -> List[float]:
```

**Profile Characteristics**:
- **Binary**: Each hour is 0W (no charging) or maximum power (e.g., 7400W)
- **Smart**: Distributes charging just before each trip, not uniformly
- **Cumulative**: Multiple trips accumulate in the same profile
- **Configurable horizon**: 7 days by default (168 hours)

**Algorithm**:
1. For each trip in the planning horizon:
   - Calculates necessary energy using `async_calcular_energia_necesaria()`
   - If `energia_necesaria_kwh > 0`:
     - Calculates necessary charging hours
     - Schedules charging `horas_carga_necesarias` before the trip
     - Fills those hours with maximum power (in Watts)
2. Returns list of 168 values (7 days × 24 hours)

**Profile Example**:
```python
# Profile for trip on Tuesday at 09:00, needs 3.9 kWh (0.53 hours)
# Scheduled charging from 08:00-09:00 (1 full hour)
[0, 0, 0, ..., 0, 7400, 0, 0, ...]  # 7400W at hour 8 (08:00-09:00)
```

---

### 3. Vehicle SOC Retrieval (`async_get_vehicle_soc`)

**File**: `custom_components/ev_trip_planner/trip_manager.py` (lines 892-930)

```python
async def async_get_vehicle_soc(self, vehicle_config: Dict[str, Any]) -> float:
```

**Sensor Handling**:
- **Configured sensor**: Reads SOC sensor state and parses numeric value
- **Sensor unavailable**: Returns 0.0 and logs warning
- **Sensor not configured**: Returns 0.0 (manual mode)
- **Invalid value**: Handles `unavailable`, `unknown`, non-numeric values

**Supported Formats**:
- `"78"` → 78.0
- `"78.5"` → 78.5
- `"78%"` → 78.0 (removes % symbol)
- `"78 %"` → 78.0 (removes spaces and symbol)

---

## 📊 Milestone 4 Sensors

### Charging Profile Sensor (`PowerProfileSensor`)

**File**: `custom_components/ev_trip_planner/sensor.py` (lines 164-220)

**Attributes**:
```python
{
    "power_profile_watts": List[float],  # Full profile (168 values)
    "total_kwh_programmed": float,       # Total programmed kWh
    "hours_with_load": int,              # Number of hours with charging > 0
    "next_charging_start": str,          # Next start time (ISO)
    "next_charging_end": str,            # Next end time (ISO)
    "vehicle_id": str,                   # Vehicle ID
    "charging_power_kw": float,          # Configured charging power
    "planning_horizon_days": int         # Planning days
}
```

**State**: `"active"` or `"idle"` (if no trips)

---

## 🧪 Implemented TDD Tests

**File**: `tests/test_power_profile_tdd.py` (10 tests, 100% passing)

### Energy Calculation Tests:
1. `test_calcular_energia_necesaria_soc_alto` - SOC 80%, no charging needed
2. `test_calcular_energia_necesaria_soc_medio` - SOC 40%, partial charging needed
3. `test_calcular_energia_necesaria_soc_bajo` - SOC 20%, full charging needed
4. `test_calcular_energia_necesaria_tiempo_insuficiente` - Alert when charging_hours > available_hours

### Profile Generation Tests:
5. `test_generar_perfil_potencia_maxima` - Profile only contains 0W or max_power
6. `test_generar_perfil_multiples_viajes` - Profile with multiple trips accumulates
7. `test_generar_perfil_sin_viajes` - Empty profile (all zeros) when no trips

### SOC Retrieval Tests:
8. `test_get_vehicle_soc_sensor_no_disponible` - Handles unavailable sensor
9. `test_get_vehicle_soc_sensor_valido` - Gets valid SOC from sensor
10. `test_get_vehicle_soc_sensor_no_configurado` - Handles vehicle without SOC sensor

**Coverage**: 85% overall, 81% in `trip_manager.py` (critical lines > 90%)

---

## 🔧 Config Flow Configuration

### New Fields (Milestone 4):

**Step 1: Basic Configuration**
- `soc_sensor`: State of Charge sensor (%, device_class: battery)
- `battery_capacity_kwh`: Total battery capacity (kWh)
- `charging_power_kw`: Maximum charging power (kW, e.g., 7.4)
- `safety_margin_percent`: Minimum post-trip SOC safety margin (%, default: 10)

**OVMS Example (Chispitas)**:
```yaml
soc_sensor: "sensor.ovms_chispitas_soc"
battery_capacity_kwh: 40.0
charging_power_kw: 7.4
safety_margin_percent: 10
```

**Renault Example (Morgan)**:
```yaml
soc_sensor: "sensor.morgan_battery_level"
battery_capacity_kwh: 27.4
charging_power_kw: 7.4
safety_margin_percent: 10
```

---

## 📈 Usage Examples

### Example 1: High SOC (No Charging Needed)
```python
# Data
soc_actual = 80%  # 32 kWh available
trip = 7.5 kWh
capacity = 40 kWh

# Calculation
post_trip = 32 - 7.5 = 24.5 kWh (61% SOC)
minimum = 40 * 0.40 = 16.0 kWh

# Result
energy_needed = max(0, 16.0 - 24.5) = 0.0 kWh
# No charging scheduled
```

### Example 2: Medium SOC (Partial Charging)
```python
# Data
soc_actual = 49%  # 19.6 kWh available
trip = 7.5 kWh
capacity = 40 kWh

# Calculation
post_trip = 19.6 - 7.5 = 12.1 kWh (30% SOC)
minimum = 40 * 0.40 = 16.0 kWh

# Result
energy_needed = max(0, 16.0 - 12.1) = 3.9 kWh
charging_hours = 3.9 / 7.4 = 0.53 hours (32 minutes)
# 1 hour of charging at maximum power scheduled
```

### Example 3: Low SOC (Full Charging)
```python
# Data
soc_actual = 20%  # 8.0 kWh available
trip = 7.5 kWh
capacity = 40 kWh

# Calculation
post_trip = 8.0 - 7.5 = 0.5 kWh (1.25% SOC) ⚠️ CRITICAL
minimum = 40 * 0.40 = 16.0 kWh

# Result
energy_needed = max(0, 16.0 - 0.5) = 15.5 kWh
charging_hours = 15.5 / 7.4 = 2.09 hours (2 hours 5 minutes)
# 3 hours of charging scheduled (rounded up)
# Alert: "Insufficient time" if available_hours < 2.09
```

---

## 🚨 Alerts and Notifications

### ⚠️ Insufficient Time Alert — NOT IMPLEMENTED

**Condition**: `es_suficiente = false` returned by `calcular_ventana_carga()`

**Intended Message** (NOT IMPLEMENTED — for reference only):
```
⚠️ Insufficient time to charge
Vehicle: chispitas
Trip: Work (7.5 kWh)
Needs: 3.9 kWh (0.53 hours)
Available: 0.25 hours (15 minutes)
Required action: Charge manually or postpone trip
```

**Current Status**: ❌ **NOT IMPLEMENTED**

The logic for detecting insufficient charging time EXISTS in [`async_calcular_energia_necesaria()`](custom_components/ev_trip_planner/trip_manager.py:1545) as `alerta_tiempo_insuficiente`, but **no sensor, notification, or UI element exposes this to users**. The user-facing function `calcular_ventana_carga()` returns `es_suficiente` instead, which could be used to build such notifications.

**Required to implement**:
- Add a sensor or notification that exposes `es_suficiente` or `alerta_tiempo_insuficiente` to the user
- Create notification service integration in `presence_monitor.py` or `schedule_monitor.py`
- Add UI indicator in the native panel

---

## 🔍 EMHASS Integration

### Complete Data Flow

1. **Trip Manager** generates charging profile (168 hours, binary)
2. **EMHASS Adapter** reads profile and creates deferrable loads
3. **EMHASS** optimizes schedule based on electricity prices
4. **Schedule Monitor** executes actions according to generated schedule
5. **Vehicle Controller** physically activates/deactivates charging

### Integration Example

```yaml
# 1. Profile generated by Trip Manager
sensor.chispitas_power_profile:
  state: "active"
  attributes:
    power_profile_watts: [0, 0, ..., 7400, 7400, 0, ...]
    total_kwh_programmed: 3.9
    hours_with_load: 1

# 2. EMHASS Adapter creates deferrable load
sensor.emhass_deferrable_load_config_0:
  state: "active"
  attributes:
    def_total_hours: 0.53
    P_deferrable_nom: 7400
    def_end_timestep: 71
    trip_id: "rec_lun_abc123"

# 3. EMHASS generates schedule
sensor.emhass_deferrable0_schedule:
  state: "02:00-03:00"  # Cheap hour

# 4. Schedule Monitor activates charging at 02:00
# 5. Vehicle Controller turns on switch.ovms_chispitas_carga
```

---

## 📋 Production Validation

### Real Vehicle Testing (Chispitas)

**Configuration**:
```yaml
vehicle_id: chispitas
soc_sensor: sensor.ovms_chispitas_soc
battery_capacity_kwh: 40.0
charging_power_kw: 7.4
safety_margin_percent: 40
```

**Test Trip**:
```yaml
dia_semana: monday
hora: "09:00"
km: 50
kwh: 7.5
descripcion: "Work"
```

**Expected Result**:
- Current SOC: 49% → 19.6 kWh
- Energy needed: 3.9 kWh
- Charging hours: 0.53 → 1 hour scheduled
- Profile: 7400W at hour 8 (08:00-09:00)
- Alert: `false` (there is enough time)

---

## 🚀 Next Steps (Milestone 4.1)

### Planned Improvements:

1. **Smart Distributed Charging**
   - Distribute charging across multiple hours (not just 1 hour)
   - Prioritize hours with cheapest electricity
   - Implement simple optimization algorithm

2. **Multiple Vehicles**
   - Support charging 2+ vehicles simultaneously
   - Load balancing based on priority
   - Home power limits

3. **SOC Prediction**
   - Use history to predict actual consumption
   - Adjust calculations based on temperature
   - Consider seasonal efficiency

4. **Climate Integration**
   - Reduce expected range if extreme cold/heat
   - Adjust energy needed based on conditions
   - Adverse weather risk alerts

5. **Charging Profile UI**
   - Chart in dashboard showing upcoming charges
   - Hours until next charging indicator
   - Forced "Charge Now" button

---

## 📚 References

### Key Files:
- `custom_components/ev_trip_planner/trip_manager.py` (lines 660-930)
- `custom_components/ev_trip_planner/sensor.py` (lines 164-220)
- `tests/test_power_profile_tdd.py` (10 tests)
- `tests/test_trip_manager_power_profile.py` (5 additional tests)

### Related Documentation:
- `docs/MILESTONE_3_IMPLEMENTATION_PLAN.md` - General implementation plan
- `docs/MILESTONE_3_REFINEMENT.md` - Refined requirements
- `docs/ISSUES_CLOSED.md` - Issue #5 (CRITICAL BUG resolved)

### Constants:
```python
# in const.py
CONF_BATTERY_CAPACITY = "battery_capacity_kwh"
CONF_CHARGING_POWER = "charging_power_kw"
CONF_SAFETY_MARGIN = "safety_margin_percent"
DEFAULT_SAFETY_MARGIN = 40  # 40% minimum SOC
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-14  
**Status**: ✅ IMPLEMENTED, TESTED & DEPLOYED  
**Next Review**: After Milestone 4.1 planning
