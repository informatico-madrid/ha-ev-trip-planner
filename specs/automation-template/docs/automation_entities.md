# Required Home Assistant Entities

This document lists all Home Assistant entities required for the EMHASS charge control automation template.

## EMHASS Plan Sensors

### Pattern 1: Per-Vehicle MPC Frozen Plan

**Entity ID**: `sensor.emhass_plan_{vehicle}_mpc_congelado`

**Description**: Contains the frozen MPC optimization plan per vehicle.

**Attributes**:
- `plan_deferrable0_horario_mpc` - Array of hourly p_deferrable0 values
- `plan_deferrable1_horario_mpc` - Array of hourly p_deferrable1 values (if multiple deferrables)
- Format: `[{"date": "2026-03-29T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]`

**Example**:
```yaml
sensor.emhass_plan_ovms_chispitas_mpc_congelado
sensor.emhass_plan_coche_morgan_mpc_congelado
```

### Pattern 2: Per-Index Schedule

**Entity ID**: `sensor.emhass_deferrable{index}_schedule`

**Description**: Contains per-deferrable schedule data.

**Attributes**:
- `horario_mpc` - Array of hourly values for that deferrable index
- `potencia_programada` - Current scheduled power

**Example**:
```yaml
sensor.emhass_deferrable0_schedule
sensor.emhass_deferrable1_schedule
```

## Vehicle State Sensors

### Home Presence Sensor

**Entity ID**: `{home_sensor}` (template variable)

**Description**: Binary sensor indicating if the vehicle is at the home location.

**Typical Implementation**:
```yaml
# Example device_tracker or zone-based sensor
device_tracker.coche_location
zone.home
```

**Expected States**: `on` / `off` or `home` / `not_home`

### Plugged Status Sensor

**Entity ID**: `{plugged_sensor}` (template variable)

**Description**: Binary sensor indicating if the vehicle is plugged in for charging.

**Typical Implementation**:
```yaml
# Example from smart-plug or EVSE
binary_sensor.coche_enchufado
sensor.plug_status
```

**Expected States**: `on` / `off`

### State of Charge (SOC) Sensor

**Entity ID**: `{soc_sensor}` (template variable)

**Description**: Sensor showing current battery state of charge percentage.

**Typical Implementation**:
```yaml
# Example from OVMS integration
sensor.coche_nivel_bateria
sensor.ovms_battery_soc
```

**Expected States**: `0` - `100` (percentage)

### Charging Status Sensor

**Entity ID**: `{charging_sensor}` (template variable)

**Description**: Binary sensor indicating if charging is currently active.

**Typical Implementation**:
```yaml
# Example from smart-plug or EVSE
binary_sensor.coche_cargando
switch.charger_status
```

**Expected States**: `on` / `off`

## Manual Mode Control

### Manual Mode Input Boolean

**Entity ID**: `input_boolean.carga_{vehicle}_modo_manual`

**Description**: Input boolean to enable/disable manual mode, preventing automation from interfering.

**Usage**: When `on`, the automation skips all charge control actions.

**Example**:
```yaml
input_boolean.carga_ovms_chispitas_modo_manual
input_boolean.carga_coche_morgan_modo_manual
```

## Charge Control Switch

### Charging Control Switch

**Entity ID**: `{charge_switch}` (template variable)

**Description**: Switch to start/stop vehicle charging.

**Typical Implementation**:
```yaml
# Example from Shelly or similar smart-plug
switch.coche_carga
switch.charger_control
```

**Actions**:
- `turn_on` - Start charging
- `turn_off` - Stop charging

## Current Power Sensor

### Instant Power Consumption

**Entity ID**: `{power_sensor}` (template variable)

**Description**: Sensor showing current power consumption in watts.

**Typical Implementation**:
```yaml
# Example from smart-plug power monitoring
sensor.coche_potencia_actual
sensor.shelly_plug_power
```

**Expected Values**: Numeric (watts)

## Sensor Pattern Selection

### Pattern Preference Input Select

**Entity ID**: `input_select.emhass_sensor_pattern`

**Description**: Input select to choose which EMHASS sensor naming pattern to use.

**Options**:
- `pattern1` - Per-vehicle MPC frozen plan
- `pattern2` - Per-index schedule

## Summary Table

| Entity Type | Entity ID Pattern | Required | Description |
|-------------|-------------------|----------|-------------|
| EMHASS Plan | `sensor.emhass_plan_{vehicle}_mpc_congelado` | Yes | MPC optimization plan |
| EMHASS Schedule | `sensor.emhass_deferrable{index}_schedule` | Yes* | Per-index schedule (*alternative) |
| Home Sensor | `{home_sensor}` | Yes | Vehicle at home location |
| Plugged Sensor | `{plugged_sensor}` | Yes | Vehicle plugged in |
| SOC Sensor | `{soc_sensor}` | Yes | Battery state of charge |
| Charging Sensor | `{charging_sensor}` | Yes | Charging active status |
| Manual Mode | `input_boolean.carga_{vehicle}_modo_manual` | Yes | Manual override control |
| Charge Switch | `{charge_switch}` | Yes | Start/stop charging |
| Power Sensor | `{power_sensor}` | Yes | Current power draw |
| Pattern Select | `input_select.emhass_sensor_pattern` | No | Pattern preference |

## Blueprint Input Definitions

When importing as a Home Assistant blueprint, the following inputs should be defined:

```yaml
blueprint:
  name: EMHASS Charge Control
  domain: automation
  input:
    vehicle_id:
      name: Vehicle ID
      description: Unique identifier for the vehicle
    home_sensor:
      name: Home Sensor
      description: Binary sensor for home presence
    plugged_sensor:
      name: Plugged Sensor
      description: Binary sensor for plug status
    soc_sensor:
      name: SOC Sensor
      description: Battery state of charge sensor
    charging_sensor:
      name: Charging Sensor
      description: Binary sensor for charging status
    modo_manual:
      name: Manual Mode Boolean
      description: Input boolean for manual override
    charge_switch:
      name: Charge Control Switch
      description: Switch to control charging
    power_sensor:
      name: Power Sensor
      description: Sensor for current power consumption
    sensor_pattern_input:
      name: Sensor Pattern
      description: Which EMHASS sensor pattern to use
```