# Dashboard Guide (DEPRECATED)

> ⚠️ **DEPRECATED**: The Lovelace Dashboard functionality is deprecated. Use the new native Home Assistant panel instead:
> **Settings → Devices & Services → EV Trip Planner → Open Panel**

This guide explains how to use the legacy Lovelace dashboard. For new installations, use the native panel.

---

## Overview

EV Trip Planner provides two dashboard templates that are automatically created when you configure a vehicle:

1. **Full Dashboard** (`ev-trip-planner-full.yaml`) - Includes charts and visualizations (requires ApexCharts)
2. **Simple Dashboard** (`ev-trip-planner-simple.yaml`) - Markdown-only, compatible with all installations

The appropriate dashboard is automatically selected based on your Lovelace configuration.

> ⚠️ **DEPRECATED**: Both dashboard templates are deprecated. Please use the native panel instead (Settings → Devices & Services → EV Trip Planner → Open Panel).

---

## Dashboard Features

### Trip Status Monitoring

The dashboard provides real-time information about your planned trips:

| Sensor | Description | Entity ID |
|--------|-------------|-----------|
| Total Trips | Number of scheduled trips | `sensor.{vehicle_id}_trips_count` |
| Next Trip | Upcoming trip departure | `sensor.{vehicle_id}_next_trip` |
| kWh Needed Today | Energy required for today's trips | `sensor.{vehicle_id}_kwh_needed_today` |

**Template Display:**
- Total scheduled trips count
- Next trip departure time and destination
- Energy requirements for today

### Deferrable Loads Monitoring

Monitor the power profile sent to EMHASS for optimization:

| Sensor | Description | Entity ID |
|--------|-------------|-----------|
| Deferrable Profile | Power schedule for EMHASS | `sensor.emhass_perfil_diferible_{entry_id}` |

**Attributes:**
- `power_profile_watts`: Array of power values (Watts) for each hour
  - `0` = No charging scheduled
  - Positive value = Charging power (e.g., `3600` = 3.6kW)
- `deferrables_schedule`: Array with timestamps and power values

**Power Profile Format:**
```json
[
  {"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"},
  {"date": "2026-03-17T15:00:00+01:00", "p_deferrable0": "3600.0"},
  ...
]
```

### EMHASS Sensor Verification

Verify that EMHASS is receiving and processing your deferrable loads correctly:

#### Step 1: Check the Sensor State

Navigate to **Developer Tools** → **States** and search for:
```
sensor.emhass_perfil_diferible_{entry_id}
```

**Verify:**
- State should be `available` or `unknown` (not `unavailable`)
- Attributes should contain `power_profile_watts` and `deferrables_schedule`

#### Step 2: Verify Power Profile Values

Check the `power_profile_watts` attribute:

```yaml
# Example values:
[0, 0, 0, 0, 0, 0, 0, 0, 3600, 3600, 0, 0, ...]
# Index = hour of week (0-167)
# Value = power in Watts
```

- `0` means no charging needed at that hour
- Positive values (e.g., `3600`) indicate charging scheduled

#### Step 3: Check EMHASS Sensors

EMHASS provides response sensors after optimization:

| EMHASS Sensor | Description |
|---------------|-------------|
| `sensor.emhass_p_deferrable` | Optimized deferrable load |
| `sensor.emhass_forecast_energy_needed` | Forecast energy |
| `sensor.emhass_optimization_status` | Last optimization result |

#### Step 4: Verify Shell Command Execution

If using shell commands to send data to EMHASS:

1. Go to **Developer Tools** → **Services**
2. Find `shell_command.emhass_day_ahead_optim`
3. Run the service
4. Check **Logbook** for execution history
5. Verify EMHASS received the data in its sensor history

---

## Dashboard Cards

### 1. EMHASS Configuration Card

Instructions for setting up the shell command to send data to EMHASS:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_YOUR_ENTRY_ID', 'power_profile_watts') | default([0]*168, true)) | tojson }}
    }' http://TU_IP_EMHASS:5000/action/dayahead-optim
```

### 2. Trip Status Card

Real-time trip information:

- **Scheduled trips**: Total count
- **Next trip**: Destination and departure time
- **kWh needed**: Energy required for today's trips

### 3. Deferrable Loads Card

Power profile visualization:

- Sensor entity and state
- Power profile length (hours configured)
- Schedule entries count
- Connection to EMHASS optimization

### 4. Vehicle Status Card

Current vehicle state:

| Sensor | Description |
|--------|-------------|
| SOC Battery | State of charge percentage |
| Range | Estimated range in km |
| Charging | Current charging status |

### 5. Presence Status Card

Home Assistant presence detection:

| Sensor | Description |
|--------|-------------|
| At Home | Vehicle/owner presence status |
| Plugged | Charger connection status |

### 6. Metrics Card (Entities)

Quick access to key sensors:

- Total trips count
- kWh needed today
- Next trip
- EMHASS deferrable profile

---

## Auto-Detection Features

### Lovelace Detection

The integration automatically detects if ApexCharts is available:

- **With ApexCharts**: Uses full dashboard with charts
- **Without ApexCharts**: Uses simple dashboard with markdown only

### Template Variables

The dashboard uses these template variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ vehicle_id }}` | Unique vehicle identifier | `chispitas`, `tesla_model_3` |
| `{{ vehicle_name }}` | Display name for vehicle | `My Tesla`, `Family EV` |

---

## Troubleshooting Dashboard Issues

### Problem: Dashboard Shows "No Available" for Sensors

**Symptoms**: Dashboard cards show sensor as unavailable.

**Solutions**:

1. **Verify sensor exists**
   - Go to **Developer Tools** → **States**
   - Search for `sensor.{vehicle_id}_trips_count`
   - Confirm it shows a value (not `unavailable`)

2. **Check entity registration**
   - Go to **Settings** → **Devices & Services** → **EV Trip Planner**
   - Verify vehicle is properly configured
   - Check for configuration errors

3. **Restart integration**
   - Go to **Settings** → **Devices & Services** → **EV Trip Planner**
   - Click three dots → **Reload**
   - Wait 30 seconds for sensors to update

### Problem: Power Profile Shows Empty or Zero

**Symptoms**: `power_profile_watts` attribute is empty or all zeros.

**Solutions**:

1. **Add trips first**
   - Create at least one trip (recurrent or punctual)
   - Power profile generates based on trip requirements

2. **Check trip energy requirements**
   - Verify trips have distance/consumption values
   - Recalculate if needed

3. **Verify planning horizon**
   - Go to vehicle configuration
   - Ensure planning horizon days is set (> 0)

### Problem: EMHASS Sensor Not Updating

**Symptoms**: Deferrable sensor exists but doesn't update.

**Solutions**:

1. **Check EMHASS configuration**
   - Verify shell command is in `configuration.yaml`
   - Confirm EMHASS API is reachable

2. **Test shell command manually**
   ```bash
   curl -X POST http://YOUR_EMHASS_IP:5000/action/dayahead-optim \
     -H "Content-Type: application/json" \
     -d '{"P_deferrable": [0,0,3600,3600,0,0,0,0]}'
   ```

3. **Check EMHASS logs**
   - Access EMHASS container/logs
   - Look for errors in data processing

### Problem: Charts Not Displaying

**Symptoms**: Power profile chart shows empty in full dashboard.

**Solutions**:

1. **Install ApexCharts**
   - Go to **HACS** → **Integrations**
   - Search for `apexcharts`
   - Install and restart Home Assistant

2. **Check sensor data**
   - Verify `power_profile_watts` has values
   - Array should have positive numbers (not all zeros)

3. **Use simple dashboard**
   - The simple dashboard works without ApexCharts
   - Markdown cards show all information as text

### Problem: Entity IDs Not Matching

**Symptoms**: Dashboard shows wrong vehicle data.

**Solutions**:

1. **Check vehicle ID**
   - Go to **Settings** → **Devices & Services** → **EV Trip Planner**
   - Note the vehicle ID used during setup

2. **Update dashboard manually**
   - Edit the YAML dashboard
   - Replace `{vehicle_id}` with correct value

3. **Delete and re-add vehicle**
   - Remove vehicle configuration
   - Add again with correct ID
   - Dashboard auto-generates with correct IDs

---

## Customizing the Dashboard

### Adding Custom Cards

Add custom cards to monitor additional metrics:

```yaml
# Example: Add charging cost estimation
- type: markdown
  title: "💰 Cost Estimate"
  content: |
    {% set kwh = states('sensor.my_vehicle_kwh_needed_today') | float(0) %}
    {% set rate = 0.15 %}  # Your electricity rate
    **Estimated cost:** {{ "%.2f"|format(kwh * rate) }} €
```

### Creating Custom Views

Add new views for specific monitoring:

```yaml
views:
  - title: "Charging History"
    path: "charging-history"
    cards:
      - type: history-graph
        entities:
          - sensor.my_vehicle_charging
        hours_to_show: 24
```

### Using with Other Integrations

Combine with other HA integrations:

```yaml
# Example: Combine with Energy dashboard
- type: energy-date-grid
  title: "Energy Usage"
```

---

## Entity Reference

### Core Sensors

| Entity ID | Type | Description |
|-----------|------|-------------|
| `sensor.{vehicle_id}_trips_count` | sensor | Total trip count |
| `sensor.{vehicle_id}_next_trip` | sensor | Next trip info |
| `sensor.{vehicle_id}_kwh_needed_today` | sensor | Today's energy needs |
| `sensor.{vehicle_id}_soc` | sensor | Battery state of charge |
| `sensor.{vehicle_id}_range` | sensor | Estimated range |
| `sensor.emhass_perfil_diferible_{entry_id}` | sensor | Deferrable load profile |

### Binary Sensors

| Entity ID | Type | Description |
|-----------|------|-------------|
| `binary_sensor.{vehicle_id}_home` | binary_sensor | At home status |
| `binary_sensor.{vehicle_id}_plugged` | binary_sensor | Plugged in status |
| `binary_sensor.{vehicle_id}_charging` | binary_sensor | Currently charging |
| `binary_sensor.{vehicle_id}_charging_needed` | binary_sensor | Charging required |

---

## Best Practices

### Dashboard Layout

1. **Group related cards**: Keep trip status, vehicle status, and EMHASS cards together
2. **Use tabs**: Create separate views for different vehicles
3. **Add refresh**: Enable auto-refresh for real-time updates

### Monitoring

1. **Check sensors daily**: Verify power profile updates each morning
2. **Review EMHASS optimization**: Confirm schedules are being generated
3. **Track energy usage**: Monitor actual vs. predicted consumption

### Maintenance

1. **Clean up old trips**: Remove completed trips to keep data current
2. **Update consumption**: Recalculate if vehicle efficiency changes
3. **Backup configuration**: Export dashboard YAML for backup

---

## Quick Reference

### Dashboard Templates

```
custom_components/ev_trip_planner/dashboard/
├── ev-trip-planner-full.yaml    # With ApexCharts
└── ev-trip-planner-simple.yaml  # Markdown only
```

### Key Sensors

```
sensor.{vehicle_id}_trips_count         # Total trips
sensor.{vehicle_id}_next_trip           # Next departure
sensor.{vehicle_id}_kwh_needed_today    # Energy needed
sensor.emhass_perfil_diferible_{entry_id} # EMHASS profile
```

### EMHASS Verification Commands

```bash
# Test EMHASS API
curl http://YOUR_EMHASS_IP:5000/status

# Send test data
curl -X POST http://YOUR_EMHASS_IP:5000/action/dayahead-optim \
  -H "Content-Type: application/json" \
  -d '{"P_deferrable": [3600,3600,0,0]}'
```

---

## Additional Resources

- [EMHASS Integration Guide](EMHASS_INTEGRATION.md)
- [Shell Command Setup](SHELL_COMMAND_SETUP.md)
- [Vehicle Control Guide](VEHICLE_CONTROL.md)
- [Notification Setup](NOTIFICATIONS.md)
- [Home Assistant Dashboard Documentation](https://www.home-assistant.io/dashboards/)
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
