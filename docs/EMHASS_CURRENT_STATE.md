# EMHASS Current State Documentation

This document describes the existing EMHASS integration in the user's Home Assistant setup.

---

## Existing Sensors

The following template sensors are currently configured for deferrable loads:

### sensor.emhass_perfil_diferible_ovms_chispitas

- **Entity ID**: `sensor.emhass_perfil_diferible_ovms_chispitas`
- **Type**: Template sensor
- **Purpose**: Deferrable load profile for vehicle "ovms_chispitas"
- **Attributes**:
  - `power_profile_watts`: Array of 168 values (one per hour for a week)
    - 0W = No charging scheduled
    - Positive value (e.g., 3600W) = Charging power in watts

### sensor.emhass_perfil_diferible_morgan

- **Entity ID**: `sensor.emhass_perfil_diferible_morgan`
- **Type**: Template sensor
- **Purpose**: Deferrable load profile for vehicle "morgan"
- **Attributes**:
  - `power_profile_watts`: Array of 168 values (one per hour for a week)
    - 0W = No charging scheduled
    - Positive value (e.g., 3600W) = Charging power in watts

---

## Power Profile Format

The `power_profile_watts` attribute contains an array of 168 values (7 days × 24 hours):

- **Index 0**: Current hour
- **Index 1**: Next hour
- ...
- **Index 167**: Hour 167 (end of week)

### Value Meaning

| Value | Meaning |
|-------|---------|
| 0 | No charging (False/Null) |
| Positive (e.g., 3600) | Charging at that power (watts) |

---

## Shell Command Configuration

### emhass_day_ahead_optim

The shell command is configured in `configuration.yaml`:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_ovms_chispitas', 'power_profile_watts') | default([0]*168) + state_attr('sensor.emhass_perfil_diferible_morgan', 'power_profile_watts') | default([0]*168)) | tojson }}
    }' http://192.168.1.100:5000/action/dayahead-optim
```

### EMHASS API Endpoint

- **URL**: http://192.168.1.100:5000/action/dayahead-optim
- **Method**: POST
- **Content-Type**: application/json
- **Purpose**: Send deferrable load profiles to EMHASS for optimization

---

## Integration Architecture

```
EV Trip Planner → Template Sensors (power_profile_watts)
                        ↓
              Shell Command (curl)
                        ↓
              EMHASS API (http://192.168.1.100:5000)
                        ↓
              EMHASS Optimization → Charging Schedule
```

---

## Notes

- These sensors are created by the EV Trip Planner integration
- The shell command aggregates both vehicle profiles into a single array
- EMHASS uses the power profile to optimize when to charge each vehicle
- The integration supports adding more vehicles by creating additional template sensors
