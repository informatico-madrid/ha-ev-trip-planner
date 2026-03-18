# Vehicle Control Guide

This guide explains how EV Trip Planner controls vehicle charging using three different strategies: Switch, Service, and Script. Choose the strategy that best matches your charging infrastructure.

---

## Overview

EV Trip Planner manages vehicle charging through a flexible strategy pattern that supports multiple control methods:

| Strategy | Best For | Complexity |
|----------|----------|------------|
| Switch | Wallboxes with switch entities | Low |
| Service | Wallboxes with service APIs | Medium |
| Script | Complex charging sequences | High |

All strategies include:
- **Presence checking**: Verifies vehicle is at home and plugged in
- **Retry logic**: Up to 3 attempts within 5 minutes on failure
- **Disconnect detection**: Resets retry counter when vehicle disconnects

---

## Prerequisites

Before configuring vehicle control, ensure you have:

1. **EV Trip Planner installed** and a vehicle configured
2. **Presence sensors configured** (home and plugged status)
3. **Charging sensor configured** (mandatory for control)
4. **Control method available** from your wallbox/charger

---

## Strategy 1: Switch Control

Use this strategy when your wallbox or charger exposes a switch entity that can turn charging on/off.

### When to Use

- Wallbox has a native switch entity (e.g., `switch.wallbox_command`)
- You want simple on/off control
- Your charger integrates with Home Assistant as a switch

### Configuration

**Step 1: Find Your Switch Entity**

1. Go to **Developer Tools** → **States**
2. Search for your wallbox entity
3. Confirm it has `switch.` prefix and supports `turn_on`/`turn_off`

**Step 2: Configure EV Trip Planner**

In the EV Trip Planner config flow (Step 4: Presence Detection):

| Field | Value |
|-------|-------|
| Control Type | `switch` |
| Charge Control Entity | `switch.your_wallbox_entity` |

### Example Switch Entities

```yaml
# Wallbox Command (community integration)
switch.wallbox_command

# Tesla Wall Connector
switch.tesla_wall_connector

# Generic Shelly Plug
switch.shelly_plug_s

# Custom template switch
switch.ev_charger
```

### Automation Example

```yaml
automation:
  - alias: "EV - Control Charging via Switch"
    trigger:
      - platform: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_charging_needed
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_home
        state: "on"
      - condition: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_plugged
        state: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.wallbox_command
```

---

## Strategy 2: Service Control

Use this strategy when your wallbox requires a service call with specific parameters to control charging.

### When to Use

- Wallbox requires specific parameters (current, phase, etc.)
- Multiple control options available (start, stop, set current)
- Charger has a Home Assistant integration with services

### Configuration

**Step 1: Discover Available Services**

1. Go to **Developer Tools** → **Services**
2. Search for your wallbox domain (e.g., `wallbox`, `going`)
3. Note the available services and their parameters

**Step 2: Configure EV Trip Planner**

| Field | Value |
|-------|-------|
| Control Type | `service` |
| Service On | `domain.service_name` |
| Service Off | `domain.service_name` |
| Data On (optional) | `{"parameter": "value"}` |
| Data Off (optional) | `{"parameter": "value"}` |

### Example Service Configurations

**Wallbox Command:**

```yaml
service_on: "wallbox.call_action"
service_off: "wallbox.call_action"
data_on:
  action: "start_charging"
  entity_id: "number.wallbox_charger"
data_off:
  action: "stop_charging"
  entity_id: "number.wallbox_charger"
```

**Go-eCharger:**

```yaml
service_on: "goe.set_charging"
service_off: "goe.set_charging"
data_on:
  charging: "true"
data_off:
  charging: "false"
```

**Custom Service with Current Setting:**

```yaml
service_on: "shell_command.set_wallbox_current"
service_off: "shell_command.stop_charging"
data_on:
  current: 16
  entity_id: switch.wallbox
```

### Automation Example

```yaml
automation:
  - alias: "EV - Control Charging via Service"
    trigger:
      - platform: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_charging_needed
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_home
        state: "on"
      - condition: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_plugged
        state: "on"
    action:
      - service: wallbox.call_action
        data:
          action: start_charging
          entity_id: number.wallbox_charger
```

---

## Strategy 3: Script Control

Use this strategy for complex charging sequences or when you need to combine multiple actions.

### When to Use

- Multiple steps required (e.g., authenticate, set current, start)
- Conditional logic needed based on time/price
- Integration with other systems

### Configuration

**Step 1: Create Control Scripts**

Create scripts in Home Assistant to handle charging control:

```yaml
script:
  ev_start_charging:
    sequence:
      - service: wallbox.call_action
        data:
          action: set_max_charging_current
          entity_id: number.wallbox_charger
          current: 16
      - delay: "00:00:02"
      - service: wallbox.call_action
        data:
          action: start_charging
          entity_id: number.wallbox_charger

  ev_stop_charging:
    sequence:
      - service: wallbox.call_action
        data:
          action: stop_charging
          entity_id: number.wallbox_charger
```

**Step 2: Configure EV Trip Planner**

| Field | Value |
|-------|-------|
| Control Type | `script` |
| Script On | `script.ev_start_charging` |
| Script Off | `script.ev_stop_charging` |

### Advanced Script Examples

**Time-Based Current Control:**

```yaml
script:
  ev_smart_charging:
    sequence:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ now().hour >= 22 or now().hour < 8 }}"
            sequence:
              - service: wallbox.call_action
                data:
                  action: set_max_charging_current
                  current: 16
        default:
          - service: wallbox.call_action
            data:
              action: set_max_charging_current
              current: 10
      - service: wallbox.call_action
        data:
          action: start_charging
```

**Multi-Step Sequence:**

```yaml
script:
  ev_full_charging_sequence:
    sequence:
      - service: switch.turn_on
        target:
          entity_id: switch.wallbox_power
      - delay: "00:00:05"
      - service: wallbox.call_action
        data:
          action: set_max_charging_current
          current: 16
      - delay: "00:00:02"
      - service: wallbox.call_action
        data:
          action: start_charging
```

---

## Presence Detection

All control strategies check presence conditions before attempting to charge.

### Required Sensors

| Sensor | Purpose | Required |
|--------|---------|----------|
| Home Sensor | Detect vehicle at home | Yes |
| Plugged Sensor | Detect charger connected | Yes |
| Charging Sensor | Detect actual charging | Yes |

### Detection Methods

**Sensor-Based (Priority 1):**

```yaml
# Binary sensors for presence
binary_sensor:
  - platform: template
    sensors:
      vehicle_home:
        value_template: "{{ is_state('device_tracker.vehicle', 'home') }}"
      vehicle_plugged:
        value_template: "{{ is_state('binary_sensor.wallbox_connected', 'on') }}"
```

**Coordinate-Based (Priority 2):**

```yaml
# GPS coordinates detection
# Configure home coordinates in EV Trip Planner config
# Vehicle coordinates from device_tracker entity
```

### Blind Mode

If no sensors are configured, EV Trip Planner assumes:
- Vehicle is always at home
- Vehicle is always plugged in

Use this only for testing or simple setups.

---

## Retry Logic

EV Trip Planner implements intelligent retry logic to handle transient failures.

### Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Attempts | 3 | Maximum retry attempts |
| Time Window | 5 minutes | Time window for attempts |

### Behavior

1. **First attempt fails**: Retry up to 2 more times within 5 minutes
2. **Max attempts reached**: Stop trying, send notification
3. **Vehicle disconnects**: Reset retry counter automatically
4. **Manual reset**: Available via service call

### Monitoring Retry State

```yaml
sensor:
  - platform: template
    sensors:
      ev_retry_status:
        value_template: |
          {% set state = states('binary_sensor.ev_trip_planner_{vehicle_id}_charging') %}
          {% if state == 'on' %}
            Charging active
          {% else %}
            {% set attempts = state_attr('sensor.ev_trip_planner_{vehicle_id}_status', 'retry_attempts') %}
            {% set max = state_attr('sensor.ev_trip_planner_{vehicle_id}_status', 'retry_max') %}
            Retry: {{ attempts }}/{{ max }}
          {% endif %}
```

---

## Notifications

Configure notifications to receive alerts when charging issues occur.

### When Notifications Sent

- Vehicle not at home but charging needed
- Vehicle not plugged in but charging needed
- Charging failed after max retries
- Trip deadline approaching

### Configuration

In EV Trip Planner config flow (Step 5: Notifications):

| Field | Value |
|-------|-------|
| Notification Service | `notify.mobile_app_your_phone` |
| Notification Devices | Select your devices |

### Notification Automation

```yaml
automation:
  - alias: "EV - Notify on Charging Issue"
    trigger:
      - platform: event
        event_type: ev_trip_planner_charging_failed
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "EV Charging Issue"
          message: >
            Unable to start charging for {{ trigger.event.data.vehicle_id }}.
            Reason: {{ trigger.event.data.reason }}
          data:
            priority: high
            channel: EV_Charging
```

---

## Troubleshooting

### Problem: Charging Not Starting

**Symptoms:** EV Trip Planner shows charging needed but charger doesn't activate.

**Solutions:**

1. **Check presence sensors**
   - Go to **Developer Tools** → **States**
   - Verify home and plugged sensors show correct values
   - Check entity ID matches configuration

2. **Verify control entity**
   - Confirm entity exists and is accessible
   - Test manually: `Developer Tools` → `Services` → `switch.turn_on`

3. **Check retry counter**
   - If max retries exceeded, reset via service
   - Verify charging sensor shows correct state

### Problem: Switch Not Found

**Symptoms:** Error "Entity not found" in logs.

**Solutions:**

1. Verify switch entity exists:
   ```bash
   # In Developer Tools → States
   search for "switch."
   ```

2. Check entity ID is correct (include domain)
3. Restart Home Assistant after adding new entities

### Problem: Service Call Fails

**Symptoms:** Service executes but charging doesn't start.

**Solutions:**

1. **Test service manually**
   - Go to **Developer Tools** → **Services**
   - Call service with correct parameters

2. **Verify service parameters**
   - Check wallbox integration documentation
   - Ensure required fields are included

3. **Check authentication**
   - Some wallboxes require initial setup
   - Verify API key/token if required

### Problem: Script Not Executing

**Symptoms:** Script shows in UI but doesn't run.

**Solutions:**

1. **Validate script syntax**
   - Go to **Developer Tools** → **YAML**
   - Check configuration

2. **Test script directly**
   - Go to **Developer Tools** → **Services**
   - Select script and click "Call Service"

3. **Check script permissions**
   - Ensure script can call required services
   - Verify no authentication issues

### Problem: Presence Detection Wrong

**Symptoms:** Vehicle shows as not home when it is (or vice versa).

**Solutions:**

1. **For sensor-based detection**
   - Check sensor state in Developer Tools
   - Verify state values: "on", "true", "home" work
   - Check sensor is not "unavailable"

2. **For GPS-based detection**
   - Verify home coordinates are accurate
   - Check distance threshold (default: 30 meters)
   - Ensure vehicle GPS sensor updates regularly

### Problem: Retry Logic Too Aggressive

**Symptoms:** Too many retry attempts, battery wear.

**Solutions:**

1. **Manual reset after each use**
   ```yaml
   script:
     ev_reset_retry:
       sequence:
         - service: ev_trip_planner.reset_retry
           data:
             vehicle_id: your_vehicle
   ```

2. **Adjust time window**
   - Modify in code: `RETRY_TIME_WINDOW_SECONDS = 300`

3. **Use external control**
   - Set control type to "none" for manual-only

---

## Best Practices

### Security

- Use dedicated user for wallbox integration
- Limit API permissions to necessary actions
- Store credentials in Home Assistant secrets

### Reliability

- Always configure presence sensors
- Test control method manually first
- Set up notifications for critical failures

### Performance

- Use native `condition: state` in automations (not templates)
- Avoid template conditions for entity state checks
- Monitor retry state to identify recurring issues

---

## Quick Reference

### Entity Naming Convention

```
Vehicle ID: {vehicle_id}

Home Sensor: binary_sensor.ev_trip_planner_{vehicle_id}_home
Plugged Sensor: binary_sensor.ev_trip_planner_{vehicle_id}_plugged
Charging Sensor: binary_sensor.ev_trip_planner_{vehicle_id}_charging
```

### Control Types

| Type | Config Field | Example |
|------|--------------|---------|
| switch | entity_id | `switch.wallbox_command` |
| service | service_on/service_off | `wallbox.call_action` |
| script | script_on/script_off | `script.ev_start_charging` |
| none | (empty) | External control only |

### Common State Values

- **Home**: "on", "true", "home"
- **Plugged**: "on", "true", "yes", "connected"
- **Charging**: "on", "true", "yes", "charging"

---

## Additional Resources

- [EMHASS Integration Guide](EMHASS_INTEGRATION.md)
- [Shell Command Setup](SHELL_COMMAND_SETUP.md)
- [Dashboard Guide](DASHBOARD.md)
- [Configuration Examples](configuration_examples.yaml)
