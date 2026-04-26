# EMHASS Setup Guide

## Introduction

This guide explains how to configure **EMHASS** (Energy Management System for Home Assistant) with the **EV Trip Planner** integration. EMHASS optimizes your home energy consumption, including electric vehicle charging, based on your trip schedules and energy tariffs.

The EV Trip Planner integration automatically generates EMHASS-compatible configuration data for your active trips, making it easy to optimize EV charging with solar PV production and time-of-use tariffs.

## What is EMHASS?

EMHASS is an energy management system that:
- **Optimizes EV charging** based on your trip schedules and energy prices
- **Integrates with solar PV** production to charge your vehicle with green energy
- **Supports time-of-use tariffs** to minimize electricity costs
- **Provides flexible deferrable loads** scheduling for multiple appliances

## Prerequisites

### 1. EMHASS Installation

First, install EMHASS in your Home Assistant instance:

```yaml
# Example HACS installation or manual installation
# See EMHASS documentation for full installation instructions
```

### 2. EV Trip Planner Configuration

Ensure you have:
- ✅ **EV Trip Planner integration** installed and configured
- ✅ **At least one vehicle** set up in EV Trip Planner
- ✅ **Active trips** with EMHASS data generated
- ✅ **EMHASS Aggregated Sensor** available for your vehicle

### 3. EMHASS Requirements

- Home Assistant 2024.x or later
- EMHASS add-on or Docker container
- Configured energy tariffs (optional but recommended)
- Solar PV integration (optional but recommended)

## EV Trip Planner EMHASS Sensors

The EV Trip Planner integration creates several sensors to support EMHASS optimization:

### Deferrable Load Sensor

**Entity ID**: `sensor.emhass_perfil_diferible_{entry_id}`

This sensor provides the 168-hour power profile (`power_profile_watts` attribute) and deferrable schedule for EMHASS optimization. The `entry_id` is the Home Assistant config entry ID (visible in the integration page URL).

### Per-Trip EMHASS Sensors

**Entity ID**: `sensor.ev_trip_planner_{vehicle_id}_trip_{trip_id}` (unique_id: `emhass_trip_{vehicle_id}_{trip_id}`)

These sensors provide per-trip EMHASS parameters including `emhass_index`, `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `power_profile_watts`, `kwh_needed`, and `deadline`. Use these for trip-specific optimization logic.

> ⚠️ **Note**: The `sensor.ev_trip_planner_{vehicle_id}_emhass_aggregated` sensor referenced in previous versions of this document does not exist in the current codebase. Use the per-trip sensors or the deferrable load sensor instead.

## EMHASS Parameters Reference

The following table describes all 6 EMHASS parameters provided by EV Trip Planner:

| Parameter | Type | Description | Example Value |
|-----------|------|-------------|---------------|
| `number_of_deferrable_loads` | integer | Number of active trips with EMHASS data | `2` |
| `def_total_hours_array` | array of floats | Total hours for each deferrable load (trip) | `[8.0, 6.5]` |
| `P_deferrable_nom_array` | array of floats | Nominal power for each trip (Watts) | `[7400, 3700]` |
| `def_start_timestep_array` | array of integers | Start timestep for each trip (0-167) | `[60, 90]` |
| `def_end_timestep_array` | array of integers | End timestep for each trip (0-167) | `[120, 150]` |
| `p_deferrable_matrix` | 2D array | Power profile matrix (Watts × 168 timesteps) | `[[0,0,...,7400,...,0]]` |

### Parameter Details

#### `number_of_deferrable_loads`
- **Type**: `integer`
- **Description**: Count of active trips with EMHASS data
- **Use**: Validates that you have trips to optimize
- **Example**: `3` means you have 3 active trips

#### `def_total_hours_array`
- **Type**: `array[float]`
- **Description**: Total charging hours needed for each trip
- **Use**: EMHASS calculates how long to charge each trip
- **Example**: `[8.0, 6.5, 4.0]` means 3 trips need 8h, 6.5h, and 4h charging

#### `P_deferrable_nom_array`
- **Type**: `array[float]`
- **Description**: Charging power for each trip in Watts
- **Use**: EMHASS uses this to calculate power consumption
- **Example**: `[7400, 7400, 11000]` means two 7.4kW chargers and one 11kW

#### `def_start_timestep_array`
- **Type**: `array[int]`
- **Description**: Start timestep for each trip (0 = 00:00, 167 = 23:45)
- **Use**: EMHASS won't start charging before this timestep
- **Example**: `[60, 90]` means trips can start charging from 15:00 and 22:30

#### `def_end_timestep_array`
- **Type**: `array[int]`
- **Description**: End timestep for each trip (deadline)
- **Use**: EMHASS ensures charging completes before this timestep
- **Example**: `[120, 150]` means trips must be charged by 06:00 and 13:00 next day

#### `p_deferrable_matrix`
- **Type**: `array[array[float]]`
- **Description**: Power profile matrix (168 timesteps × 15-minute intervals)
- **Use**: Detailed power consumption profile for optimization
- **Example**: `[[0,0,...,7400,...,0]]` shows power consumption over 24 hours

## Jinja2 Templates for EMHASS

### Basic Template (All 6 Parameters)

Use this template in your EMHASS `optimize.yaml` configuration:

```yaml
{# EMHASS Configuration for EV Trip Planner #}
{# Generated from EV Trip Planner EMHASS Aggregated Sensor #}
{% set sensor_id = 'sensor.ev_trip_planner_your_vehicle_id_emhass_aggregated' %}

# Number of deferrable loads (active trips)
number_of_deferrable_loads: {{ state_attr(sensor_id, 'number_of_deferrable_loads') | default(0) }}

# Total hours for each deferrable load
def_total_hours_array: {{ state_attr(sensor_id, 'def_total_hours_array') | default([], true) | tojson }}

# Nominal power for each deferrable load (Watts)
p_deferrable_nom_array: {{ state_attr(sensor_id, 'p_deferrable_nom_array') | default([], true) | tojson }}

# Start timestep for each deferrable load
def_start_timestep_array: {{ state_attr(sensor_id, 'def_start_timestep_array') | default([], true) | tojson }}

# End timestep for each deferrable load
def_end_timestep_array: {{ state_attr(sensor_id, 'def_end_timestep_array') | default([], true) | tojson }}

# Power profile matrix (Watts per timestep)
p_deferrable_matrix: {{ state_attr(sensor_id, 'p_deferrable_matrix') | default([], true) | tojson }}
```

### Template with Fallback Values

This template includes default values if the sensor is unavailable:

```yaml
{% set sensor_id = 'sensor.ev_trip_planner_your_vehicle_id_emhass_aggregated' %}
{% set na_loads = 0 %}
{% set na_hours = [] %}
{% set na_power = [] %}
{% set na_start = [] %}
{% set na_end = [] %}
{% set na_matrix = [] %}

{% set emhass_state = states(sensor_id) %}
{% if emhass_state and emhass_state != 'unknown' and emhass_state != 'unavailable' %}
  {% set na_loads = state_attr(sensor_id, 'number_of_deferrable_loads') | default(0) %}
  {% set na_hours = state_attr(sensor_id, 'def_total_hours_array') | default([], true) %}
  {% set na_power = state_attr(sensor_id, 'p_deferrable_nom_array') | default([], true) %}
  {% set na_start = state_attr(sensor_id, 'def_start_timestep_array') | default([], true) %}
  {% set na_end = state_attr(sensor_id, 'def_end_timestep_array') | default([], true) %}
  {% set na_matrix = state_attr(sensor_id, 'p_deferrable_matrix') | default([], true) %}
{% endif %}

number_of_deferrable_loads: {{ na_loads }}
def_total_hours_array: {{ na_hours | tojson }}
p_deferrable_nom_array: {{ na_power | tojson }}
def_start_timestep_array: {{ na_start | tojson }}
def_end_timestep_array: {{ na_end | tojson }}
p_deferrable_matrix: {{ na_matrix | tojson }}
```

### Individual Parameter Templates

If you need to reference individual parameters:

```yaml
# Just the number of trips
number_of_deferrable_loads: {{ states('sensor.ev_trip_planner_your_vehicle_id_emhass_aggregated') | int | default(0) }}

# Just total hours
def_total_hours_array: {{ state_attr('sensor.ev_trip_planner_your_vehicle_id_emhass_aggregated', 'def_total_hours_array') | default('[]') | replace("'", '"') }}
```

## EMHASS Configuration Example

Complete EMHASS `optimize.yaml` configuration using EV Trip Planner data:

```yaml
# EMHASS optimize configuration
# Location: /config/emhass/optimize.yaml

algorithm:
  name: 'mixed_integer'  # or 'predictive'
  params:
    def_total_hours_array: ${def_total_hours_array}
    p_deferrable_nom_array: ${p_deferrable_nom_array}
    def_start_timestep_array: ${def_start_timestep_array}
    def_end_timestep_array: ${def_end_timestep_array}
    p_deferrable_matrix: ${p_deferrable_matrix}

placeholders:
  number_of_deferrable_loads: ${number_of_deferrable_loads}

optimization:
  set_use_battery: true
  battery_discharge_power: 3000
  battery_soc_max: 1.0
  battery_soc_min: 0.2

costfun:
  option: 'cost_min'  # or 'self_consumption' or 'cost_min_CO2'

solver:
  name: 'glpk'  # or 'cbc' or 'highs'

pv_power_forecast:
  model: 'persistence'  # or 'nested_svm'

load_cost_forecast:
  model: 'persistence'  # or 'nested_svm'

params:
  def_total_hours: ${def_total_hours_array}
  p_deferrable_nom: ${p_deferrable_nom_array}
  def_start_timestep: ${def_start_timestep_array}
  def_end_timestep: ${def_end_timestep_array}
  p_deferrable: ${p_deferrable_matrix}
```

## Getting the Template from EV Trip Planner

### Method 1: Frontend Panel (Recommended)

1. Open **EV Trip Planner** panel in Home Assistant
2. Scroll to **EMHASS Configuration** section
3. Click **📋 Copy Template** button
4. Paste into your EMHASS configuration file

### Method 2: Manual Template Creation

Use the **Basic Template** section above and replace `your_vehicle_id` with your actual vehicle ID.

## Troubleshooting

### EMHASS Sensor Not Available

**Problem**: `sensor.ev_trip_planner_{vehicle_id}_emhass_aggregated` shows as `unavailable` or `unknown`

**Solutions**:
1. **Check active trips**: Ensure you have at least one active trip in EV Trip Planner
2. **Run trip generation**: Use the "Generate Trips" service to create EMHASS data
3. **Check vehicle ID**: Verify the sensor entity ID matches your vehicle ID
4. **Reload resources**: In Home Assistant Developer Tools → YAML → Reload Resources

### Empty Arrays in Parameters

**Problem**: All EMHASS parameters show empty arrays `[]`

**Solutions**:
1. **Add trips with EMHASS data**: Create recurring or punctual trips with kW values
2. **Check charging power**: Ensure trips have valid `kwh` and `km` values
3. **Regenerate EMHASS data**: Call the `publish_deferrable_loads` service

### Template Syntax Errors

**Problem**: Jinja2 template fails with syntax errors

**Solutions**:
1. **Check quotes**: Use `replace("'", '"')` to convert single quotes to double quotes
2. **Validate array format**: Ensure arrays are properly formatted `[1.0, 2.0]`
3. **Test sensor availability**: Use `default('[]')` for fallback values

### EMHASS Optimization Not Working

**Problem**: EMHASS runs but doesn't optimize EV charging

**Solutions**:
1. **Verify parameter format**: EMHASS expects arrays, not single values
2. **Check number_of_deferrable_loads**: Must be > 0 for optimization to run
3. **Review EMHASS logs**: Check for parameter parsing errors
4. **Validate timestep values**: Ensure timesteps are in range 0-167

### Copy Button Not Working

**Problem**: Copy button in EV Trip Planner panel doesn't copy template

**Solutions**:
1. **Use HTTPS**: Clipboard API requires HTTPS (or localhost)
2. **Check browser permissions**: Allow clipboard access for Home Assistant
3. **Manual copy**: Select template text and use Ctrl+C (Cmd+C on Mac)

## Advanced Configuration

### Multiple Vehicles

If you have multiple vehicles with EV Trip Planner:

```yaml
# For vehicle 1
{% set emhass_v1 = states('sensor.ev_trip_planner_vehicle1_emhass_aggregated') %}
# For vehicle 2
{% set emhass_v2 = states('sensor.ev_trip_planner_vehicle2_emhass_aggregated') %}

# Combine both vehicles
number_of_deferrable_loads: {{ emhass_v1.attributes.number_of_deferrable_loads | default(0) + emhass_v2.attributes.number_of_deferrable_loads | default(0) }}
```

### Solar PV Integration

EMHASS can optimize EV charging with solar production:

```yaml
pv_power_forecast:
  model: 'nested_svm'  # Requires historical data
  prediction_horizon: 24  # Hours
```

### Time-of-Use Tariffs

Configure electricity prices for cost optimization:

```yaml
load_cost_forecast:
  model: 'nested_svm'  # Requires price sensor data
  prediction_horizon: 24  # Hours
```

## Support and Documentation

- **EV Trip Planner**: [GitHub Issues](https://github.com/your-repo/ev-trip-planner/issues)
- **EMHASS Documentation**: [EMHASS GitHub](https://github.com/davidusb-geek/emhass)
- **Home Assistant Community**: [EV Trip Planner Thread](https://community.home-assistant.io/t/ev-trip-planner)

## Changelog

### Version 1.0 (2026-04-12)
- Initial EMHASS setup documentation
- Added 6 EMHASS parameters reference
- Included Jinja2 templates for all use cases
- Added troubleshooting section
- Documented frontend panel copy button feature
