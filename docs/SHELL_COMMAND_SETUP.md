# Shell Command Setup Guide

This guide provides detailed instructions for setting up shell commands to integrate EV Trip Planner with EMHASS for optimized EV charging.

---

## Overview

The shell command sends your vehicle's power profile to EMHASS for optimization. EV Trip Planner generates a template sensor with charging schedule data, and the shell command sends this data to EMHASS via its REST API.

**Data Flow:**
```
EV Trip Planner → Template Sensor → Shell Command → EMHASS API
```

---

## Prerequisites

Before configuring the shell command, ensure:

1. EV Trip Planner is installed and configured with at least one vehicle
2. EMHASS add-on is installed and running
3. You have scheduled at least one trip in EV Trip Planner

---

## Copy/Paste Configuration

### Single Vehicle

Add this to your Home Assistant `configuration.yaml`:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_YOUR_VEHICLE_ID', 'power_profile_watts') | default([0]*168, true)) | tojson }}
    }' http://YOUR_EMHASS_IP:5000/action/dayahead-optim
```

### Two Vehicles

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (
        state_attr('sensor.emhass_perfil_diferible_vehicle_1', 'power_profile_watts') | default([0]*168, true) +
        state_attr('sensor.emhass_perfil_diferible_vehicle_2', 'power_profile_watts') | default([0]*168, true)
      ) | tojson }}
    }' http://YOUR_EMHASS_IP:5000/action/dayahead-optim
```

---

## Parameter Explanation

### curl Flags

| Flag | Purpose |
|------|---------|
| `-i` | Include HTTP response headers in output |
| `-H "Content-Type: application/json"` | Tell EMHASS we are sending JSON data |
| `-X POST` | Use HTTP POST method (required by EMHASS API) |
| `-d ' {...} '` | Send the JSON data in the request body |

### Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `YOUR_VEHICLE_ID` | Your vehicle identifier from EV Trip Planner | `ovms_chispitas`, `tesla_model_3` |
| `YOUR_EMHASS_IP` | IP address of your EMHASS instance | `192.168.1.201` |

### Jinja2 Template Filters

| Filter | Purpose |
|--------|---------|
| `state_attr(...)` | Retrieves an attribute from a Home Assistant sensor |
| `default([0]*168, true)` | Provides default values if sensor is unavailable |
| `tojson` | Converts Python list to valid JSON array |

### Sensor Entity

The template references this sensor:
- Entity ID: `sensor.emhass_perfil_diferible_{vehicle_id}`
- Attribute: `power_profile_watts` (array of 168 values)

---

## Configuration Steps

### Step 1: Edit configuration.yaml

1. Open your Home Assistant configuration.yaml file
2. Add a `shell_command:` section at the top level
3. Paste one of the configurations above
4. Replace placeholders:
   - `YOUR_VEHICLE_ID` → your vehicle identifier
   - `YOUR_EMHASS_IP` → your EMHASS IP address

### Step 2: Validate Configuration

1. Go to **Developer Tools** → **YAML**
2. Click **Check Configuration**
3. Fix any errors if reported

### Step 3: Restart Home Assistant

1. If validation passes, click **Restart Home Assistant**
2. Wait for Home Assistant to fully restart

### Step 4: Test the Command

1. Navigate to **Developer Tools** → **Services**
2. Search for `shell_command.emhass_day_ahead_optim`
3. Click **Call Service**

**Expected Result:**
- HTTP/1.1 200 OK response from EMHASS
- No error messages in Home Assistant logs

---

## Understanding the Power Profile

### Array Structure

The `power_profile_watts` attribute contains 168 values:
- 7 days × 24 hours = 168 hours
- Each value represents charging power in watts for that hour

### Value Meaning

| Value | Meaning |
|-------|---------|
| `0` | No charging scheduled at this hour |
| Positive (e.g., `3600`) | Charging at 3600 watts (3.6 kW) |

### Example Array

```
[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3600, 3600, 3600, 0, 0, 0, ...]
  |---Hour 0-13 (night)---|---Hour 14-16 (charging)---|---Hour 17+ (after)---|
```

---

## Multiple Vehicles

### Three or More Vehicles

For more than two vehicles, add additional aggregations:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (
        state_attr('sensor.emhass_perfil_diferible_vehicle_1', 'power_profile_watts') | default([0]*168, true) +
        state_attr('sensor.emhass_perfil_diferible_vehicle_2', 'power_profile_watts') | default([0]*168, true) +
        state_attr('sensor.emhass_perfil_diferible_vehicle_3', 'power_profile_watts') | default([0]*168, true)
      ) | tojson }}
    }' http://YOUR_EMHASS_IP:5000/action/dayahead-optim
```

**Important:** All vehicles must have the same planning horizon (default: 7 days = 168 values) for proper aggregation.

---

## Common Issues and Solutions

### Sensor Not Found

**Error:** `UndefinedError: 'state_attr'`

**Cause:** The template sensor doesn't exist yet.

**Solution:**
1. Ensure at least one vehicle is configured in EV Trip Planner
2. Add at least one trip with a departure time
3. Wait for the sensor to be created

### EMHASS Connection Refused

**Error:** `Failed to connect to host`

**Cause:** EMHASS is not reachable.

**Solution:**
1. Verify EMHASS is running
2. Check IP address and port
3. Verify network connectivity

### Empty Power Profile

**Error:** All values are 0

**Cause:** No trips scheduled or trips are in the past.

**Solution:**
1. Add trips with future departure times
2. Verify departure time and required charge are set

---

## Automating the Command

### Basic Automation

Run the optimization every hour:

```yaml
automation:
  - alias: "EMHASS Hourly Optimization"
    trigger:
      - platform: time
        at: "00:00:00"
      - platform: time
        at: "01:00:00"
      - platform: time
        at: "02:00:00"
      - platform: time
        at: "03:00:00"
      - platform: time
        at: "04:00:00"
      - platform: time
        at: "05:00:00"
      - platform: time
        at: "06:00:00"
      - platform: time
        at: "07:00:00"
      - platform: time
        at: "08:00:00"
      - platform: time
        at: "09:00:00"
      - platform: time
        at: "10:00:00"
      - platform: time
        at: "11:00:00"
      - platform: time
        at: "12:00:00"
      - platform: time
        at: "13:00:00"
      - platform: time
        at: "14:00:00"
      - platform: time
        at: "15:00:00"
      - platform: time
        at: "16:00:00"
      - platform: time
        at: "17:00:00"
      - platform: time
        at: "18:00:00"
      - platform: time
        at: "19:00:00"
      - platform: time
        at: "20:00:00"
      - platform: time
        at: "21:00:00"
      - platform: time
        at: "22:00:00"
      - platform: time
        at: "23:00:00"
    action:
      - service: shell_command.emhass_day_ahead_optim
```

### Compact Automation

Using a time pattern:

```yaml
automation:
  - alias: "EMHASS Hourly Optimization"
    trigger:
      - platform: time_pattern
        hours: "/1"
    action:
      - service: shell_command.emhass_day_ahead_optim
```

---

## Testing the Integration

### Verify Sensor Data

1. Go to **Developer Tools** → **States**
2. Search for: `sensor.emhass_perfil_diferible_`
3. Click on the sensor to view attributes
4. Verify `power_profile_watts` has values

### Verify EMHASS Received Data

1. Execute the shell command via Developer Tools
2. Check EMHASS sensors for `P_deferrable` values
3. Verify values match your EV Trip Planner configuration

---

## Advanced Configuration

### Using Authentication

If EMHASS requires authentication:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_YOUR_VEHICLE_ID', 'power_profile_watts') | default([0]*168, true)) | tojson }}
    }' http://YOUR_EMHASS_IP:5000/action/dayahead-optim
```

### Using HTTPS

For secure connections:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -k -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_YOUR_VEHICLE_ID', 'power_profile_watts') | default([0]*168, true)) | tojson }}
    }' https://YOUR_EMHASS_IP:5000/action/dayahead-optim
```

---

## Related Documentation

- [EMHASS Integration Guide](EMHASS_INTEGRATION.md)
- [Configuration Examples](configuration_examples.yaml)
- [Dashboard Guide](DASHBOARD.md)
