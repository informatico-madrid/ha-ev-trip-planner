# EMHASS Integration Guide

This guide provides step-by-step instructions to integrate EV Trip Planner with EMHASS for optimized EV charging.

---

## Prerequisites

Before starting, ensure you have:

- Home Assistant installed and running
- EMHASS add-on installed and configured
- EV Trip Planner integration installed
- At least one vehicle configured in EV Trip Planner

---

## Step 1: Install EMHASS Add-on

### Home Assistant OS / Supervised

1. Open Home Assistant and go to **Settings** → **Add-ons**
2. Click the **Add-on Store** button (bottom right)
3. Click the three dots menu (top right) → **Repositories**
4. Add the EMHASS repository:
   ```
   https://github.com/davidusb-ge/emhass
   ```
5. Find **EMHASS** in the add-on store and click **Install**
6. Configure the add-on with your settings:
   ```json
   {
     "latitude": 40.7128,
     "longitude": -74.0060,
     "tz": "America/New_York",
     "forecast_days": 2,
     "optimization_time_step": 15,
     "def_total_hours": 24,
     "weather_config": {
       "solar": "forecast",
       "number_of_years": 1,
       "solar_power": 5000
     }
   }
   ```
7. Start the add-on and enable **Start on boot**

### Standalone Installation

If running EMHASS separately:

1. Install Docker: `docker pull davidusbf/emhass`
2. Run the container:
   ```bash
   docker run -d \
     -p 5000:5000 \
     -v ./emhass_data:/data \
     -e TZ=America/New_York \
     davidusbf/emhass
   ```
3. Access EMHASS at `http://YOUR_EMHASS_IP:5000`

### Verify EMHASS is Running

1. Open your browser to `http://YOUR_EMHASS_IP:5000`
2. You should see the EMHASS web interface
3. Check the **Configuration** page to ensure deferrable loads are enabled

---

## Integration Steps

### Step 1: Copy Shell Command to configuration.yaml

1. Open your Home Assistant `configuration.yaml` file
2. Add the shell command configuration under the `shell_command:` section

**Single Vehicle Configuration:**

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ (state_attr('sensor.emhass_perfil_diferible_YOUR_VEHICLE_ID', 'power_profile_watts') | default([0]*168, true)) | tojson }}
    }' http://YOUR_EMHASS_IP:5000/action/dayahead-optim
```

**Replace placeholders:**
- `YOUR_VEHICLE_ID`: Your vehicle identifier (e.g., `ovms_chispitas`, `morgan`, `tesla_model_3`)
- `YOUR_EMHASS_IP`: IP address of your EMHASS instance (e.g., `192.168.1.100`)

**Multiple Vehicles Configuration:**

If you have multiple vehicles, aggregate their power profiles:

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

### Step 2: Restart Home Assistant

After adding the shell command to your configuration.yaml:

1. Go to **Developer Tools** → **YAML**
2. Click **Check Configuration** to validate your YAML
3. If valid, click **Restart Home Assistant**
4. Wait for Home Assistant to fully restart

**Alternative method:**
1. Go to **Settings** → **System**
2. Click the power button (top right)
3. Select **Restart Home Assistant**

---

### Step 3: Test Shell Command Execution

Once Home Assistant has restarted:

1. Navigate to **Developer Tools** → **Services**
2. Search for `shell_command.emhass_day_ahead_optim`
3. Click **Call Service**

**Expected response:**
- You should see a successful HTTP response from EMHASS
- The response should include status code 200 or similar success indicator

**If the service fails:**
- Verify EMHASS is running and accessible
- Check the sensor entity exists: `sensor.emhass_perfil_diferible_{vehicle_id}`
- Review Home Assistant logs for error details

---

### Step 4: Verify EMHASS API Receives Data

After executing the shell command, verify that EMHASS received the deferrable load data:

**Option A: Check EMHASS Logs**

1. Access your EMHASS add-on logs
2. Look for the POST request containing `P_deferrable`
3. Verify the array contains your expected power profile values

**Option B: Check EMHASS Sensors**

EMHASS provides sensors that show the received deferrable loads. Check for:
- `sensor.p_deferrable` or similar sensors
- The values should match the power profile from your EV Trip Planner

**Option C: Use Developer Tools**

1. Go to **Developer Tools** → **States**
2. Search for your EV Trip Planner sensor: `sensor.emhass_perfil_diferible_{vehicle_id}`
3. Verify the `power_profile_watts` attribute contains non-zero values (if trips are scheduled)

---

## Understanding Power Profiles

EV Trip Planner creates template sensors with two important attributes:

### power_profile_watts

The `power_profile_watts` attribute contains an array of power values:

| Value | Meaning |
|-------|---------|
| `0` | No charging scheduled at this hour |
| Positive (e.g., `3600`) | Charging power in watts (3.6 kW) |

**Array structure:**
- Default length: 168 values (7 days × 24 hours)
- Each index represents one hour in the planning horizon

### deferrables_schedule

The `deferrables_schedule` attribute contains detailed schedule information in JSON format:

```json
[
  {"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"},
  {"date": "2026-03-17T15:00:00+01:00", "p_deferrable0": "3600.0"},
  ...
]
```

**Fields:**
- `date`: ISO 8601 timestamp for the hour
- `p_deferrable{index}`: Power value in watts for each deferrable load (0, 1, 2, ...)

---

## Troubleshooting

### Sensor Not Found

**Problem:** Error message "sensor not found"

**Solution:**
1. Verify the vehicle was configured in EV Trip Planner
2. Check that the sensor entity exists: `sensor.emhass_perfil_diferible_{vehicle_id}`
3. Ensure the vehicle has at least one trip scheduled

### EMHASS Connection Failed

**Problem:** curl command fails with connection error

**Solution:**
1. Verify EMHASS is running: `http://YOUR_EMHASS_IP:5000`
2. Check network connectivity from HA to EMHASS
3. Verify EMHASS API endpoint is correct (`/action/dayahead-optim`)
4. Check EMHASS authentication settings if enabled
5. Verify the correct port (default 5000) is open

### Empty Power Profile

**Problem:** All values in the array are 0

**Solution:**
1. Check that trips are scheduled in EV Trip Planner
2. Verify planning horizon includes the trip deadline
3. Ensure the trip deadline is in the future
4. Check that the departure time is set for each trip
5. Verify consumption sensor is configured

### Invalid JSON Response

**Problem:** EMHASS returns invalid JSON or error message

**Solution:**
1. Check EMHASS logs for detailed error information
2. Verify the POST data format is correct
3. Ensure EMHASS is properly configured for deferrable loads
4. Check that the power profile array has the correct length

### Power Profile Array Length Mismatch

**Problem:** EMHASS expects 168 values but receives different length

**Solution:**
1. Verify planning horizon is set to 7 days (168 hours)
2. Check the `default([0]*168)` filter in the shell command
3. Ensure the sensor attribute has 168 values

### EMHASS Not Optimizing

**Problem:** EMHASS runs but doesn't produce optimized schedule

**Solution:**
1. Verify deferrable loads are published correctly
2. Check EMHASS sensors for P_deferrable values
3. Ensure load configuration is enabled in EMHASS
4. Check for forecast data availability

### Template Sensor Not Updating

**Problem:** Sensor exists but attributes don't change

**Solution:**
1. Check EV Trip Planner trip configuration
2. Verify departure time and charging power settings
3. Restart EV Trip Planner integration
4. Check Home Assistant logs for errors

---

## Automation Setup (Optional)

To automatically run the shell command on a schedule:

1. Create a new automation in Home Assistant
2. Set a trigger (e.g., every hour)
3. Add a **Call Service** action
4. Select `shell_command.emhass_day_ahead_optim`

```yaml
automation:
  - alias: "EMHASS Daily Optimization"
    trigger:
      - platform: time
        at: "00:00:00"
    action:
      - service: shell_command.emhass_day_ahead_optim
```

---

## Integration Flow Summary

```
EV Trip Planner
      ↓
Template Sensor: sensor.emhass_perfil_diferible_{vehicle_id}
      ↓
    Attributes: power_profile_watts (array)
      ↓
Shell Command (curl to EMHASS)
      ↓
EMHASS Optimization Engine
      ↓
Optimized Charging Schedule
```

---

## Additional Resources

- [Shell Command Example](SHELL_COMMAND_SETUP.md)
- [EMHASS Add-on Documentation](https://github.com/davidusb-ge/emhass)
- [EV Trip Planner Dashboard](DASHBOARD.md)
