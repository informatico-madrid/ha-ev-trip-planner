# Notification Setup Guide

This guide explains how to configure notifications in EV Trip Planner to receive alerts about charging status, trip deadlines, and issues requiring attention.

---

## Overview

EV Trip Planner can send notifications when action is needed or when charging issues occur. Notifications help ensure your vehicle is ready for planned trips.

### Notification Features

- **Smart alerts**: Notifications only when intervention is needed
- **Multiple channels**: Support for all Home Assistant notification services
- **Device targeting**: Send to specific devices or all devices
- **Trip context**: Include destination, energy needed, and deadline info

---

## Prerequisites

Before configuring notifications, ensure you have:

1. **EV Trip Planner installed** and a vehicle configured
2. **Notification service available** in Home Assistant
3. **Mobile app configured** (for push notifications)

---

## Supported Notification Services

EV Trip Planner integrates with any Home Assistant notify service. Common options include:

### Mobile App Notifications

| Service | Platform | Best For |
|---------|----------|----------|
| `notify.mobile_app_your_phone` | iOS/Android | Push notifications |
| `notify.mobile_app_iphone` | iOS only | Apple Push Notification |
| `notify.mobile_app_android` | Android only | FCM/GCM notifications |

### Other Notification Services

| Service | Platform | Best For |
|---------|----------|----------|
| `notify.persistent_notification` | HA UI | Dashboard alerts |
| `notify.telegram` | Telegram | Messaging apps |
| `notify.email` | Email | Non-urgent alerts |
| `notify.alexa_media` | Alexa | Voice announcements |

---

## Configuration

### Step 1: Configure Notification Service

During EV Trip Planner setup (Config Flow Step 5: Notifications):

1. Open **Settings** → **Devices & Services** → **EV Trip Planner**
2. Add or select your vehicle
3. Complete Steps 1-4 normally
4. In **Step 5: Notifications**:

| Field | Description | Required |
|-------|-------------|----------|
| Notification Service | Select notify service (e.g., `notify.mobile_app_your_phone`) | No |
| Notification Devices | Choose specific devices to notify | No |

### Step 2: Verify Notification Service

After configuration, test that notifications work:

```yaml
service: notify.mobile_app_your_phone
data:
  title: "Test Notification"
  message: "EV Trip Planner notifications are working!"
```

Run this via **Developer Tools** → **Services** to verify.

---

## Notification Types

EV Trip Planner sends notifications in these scenarios:

### 1. Vehicle Not at Home

**Trigger**: Charging needed but vehicle is away.

**Message Example**:
```
⚠️ EV Trip Planner: my_vehicle
Charging required but not possible: Vehicle not at home

Trip destination: Office
Energy needed: 15.2 kWh
Deadline: 08:00

Please connect the vehicle or ensure it's at home.
```

### 2. Vehicle Not Plugged In

**Trigger**: Charging scheduled but charger not connected.

**Message Example**:
```
⚠️ EV Trip Planner: my_vehicle
Charging required but not possible: Vehicle not plugged in

Trip destination: Airport
Energy needed: 45.0 kWh
Deadline: 06:00

Please connect the vehicle or ensure it's at home.
```

### 3. Charging Failed (After Retries)

**Trigger**: All retry attempts exhausted.

**Message Example**:
```
⚠️ EV Trip Planner: my_vehicle
Charging failed after maximum retries

Vehicle: Tesla Model 3
Status: Not charging
Please check manually.
```

---

## Notification Channels

### Mobile App (Push Notifications)

**Setup**:

1. Install Home Assistant app on your phone
2. Enable notifications in app settings
3. Grant notification permissions

**Configuration**:
```yaml
# In EV Trip Planner config flow
notification_service: notify.mobile_app_your_phone
notification_devices:
  - device_id_1
  - device_id_2
```

### Telegram

**Setup**:

1. Configure Telegram bot via HA integrations
2. Get chat ID
3. Add `notify.telegram` service

**Configuration**:
```yaml
# In configuration.yaml
telegram_bot:
  - bot_token: YOUR_BOT_TOKEN

notify:
  - name: telegram
    platform: telegram
    chat_id: YOUR_CHAT_ID
```

### Email Notifications

**Setup**:

1. Configure SMTP in Home Assistant
2. Set up email notifications

**Configuration**:
```yaml
# In configuration.yaml
notify:
  - name: gmail
    platform: smtp
    server: smtp.gmail.com
    port: 587
    username: your_email@gmail.com
    password: your_app_password
    sender: your_email@gmail.com
    recipient: recipient@example.com
```

---

## Customizing Notification Content

### Using Automation Templates

Create custom automations to modify notification behavior:

```yaml
automation:
  - alias: "EV - Custom Charging Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_home
        to: "off"
    condition:
      - condition: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_charging_needed
        state: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔌 EV Charging Alert"
          message: |
            Vehicle needs charging but is not at home!
            Trip: {{ state_attr('sensor.ev_trip_planner_{vehicle_id}_next_trip', 'destination') }}
            Deadline: {{ state_attr('sensor.ev_trip_planner_{vehicle_id}_next_trip', 'departure_time') }}
          data:
            priority: high
            ttl: 0
            interruption-level: timeSensitive
```

### Customizing with Event Data

Listen for EV Trip Planner events and create custom notifications:

```yaml
automation:
  - alias: "EV - Custom Notification on Event"
    trigger:
      - platform: event
        event_type: ev_trip_planner_{vehicle_id}_charging_not_possible
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚡ EV Trip Planner Alert"
          message: >
            {% set vehicle = trigger.event.data.vehicle_id %}
            {% set reason = trigger.event.data.reason %}
            {{ vehicle }}: {{ reason }}
          data:
            subtitle: "Tap to open Home Assistant"
            actions:
              - action: "URI"
                title: "Open Dashboard"
                uri: "/ui"
```

---

## Troubleshooting

### Problem: Notifications Not Received

**Symptoms**: EV Trip Planner should send notifications but nothing arrives.

**Solutions**:

1. **Verify notification service**
   - Go to **Developer Tools** → **Services**
   - Test your notify service directly
   - Confirm it works with other automations

2. **Check mobile app permissions**
   - Open Home Assistant app
   - Go to Settings → Notifications
   - Enable notifications for the app

3. **Check device ID**
   - Go to **Settings** → **Devices & Services** → **Entities**
   - Find your mobile app device
   - Copy the exact device_id

### Problem: Wrong Notification Service

**Symptoms**: Notifications go to wrong device or service.

**Solutions**:

1. **Check service name**
   - In **Developer Tools** → **Services**, find your notify service
   - Ensure it matches exactly (e.g., `notify.mobile_app_your_phone`)

2. **Reconfigure in EV Trip Planner**
   - Delete and re-add the vehicle
   - Select correct notification service

### Problem: Too Many Notifications

**Symptoms**: Receiving duplicate or excessive notifications.

**Solutions**:

1. **Check for multiple triggers**
   - Review your automations for duplicate triggers
   - Use conditions to prevent duplicate sends

2. **Add notification cooldown**
   ```yaml
   automation:
     - alias: "EV - Cooldown Example"
       trigger:
         - platform: state
           entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_charging_needed
       condition:
         - condition: template
           value_template: "{{ now() - this.attributes.last_triggered | default(as_datetime('1970-01-01')) > timedelta(minutes=30) }}"
       action:
         - service: notify.mobile_app_your_phone
           data:
             message: "Charging needed!"
   ```

### Problem: Notifications Show as Read Immediately

**Symptoms**: Notifications appear but disappear immediately on mobile.

**Solutions**:

1. **Check notification ID**
   - EV Trip Planner uses `notification_id: ev_trip_planner_{vehicle_id}`
   - This replaces previous notifications with same ID

2. **Modify automation for unique ID**
   - Add unique identifier to notification_id
   ```yaml
   service: notify.mobile_app_your_phone
   data:
     notification_id: "ev_trip_planner_{{ now().timestamp() }}"
   ```

---

## Testing Notifications

### Manual Test

Send a test notification via Developer Tools:

```yaml
service: notify.mobile_app_your_phone
data:
  title: "EV Trip Planner Test"
  message: "If you receive this, notifications are configured correctly!"
```

### Test with Presence Monitor

Trigger a notification by simulating a condition:

1. Go to **Developer Tools** → **States**
2. Set `binary_sensor.ev_trip_planner_{vehicle_id}_home` to `off`
3. Set `binary_sensor.ev_trip_planner_{vehicle_id}_charging_needed` to `on`
4. Wait for notification (should arrive within 60 seconds)

---

## Best Practices

### Security

- Use app-specific passwords for email notifications
- Never expose credentials in configuration files
- Use Home Assistant secrets for sensitive data

### Reliability

- Always test notifications after configuration
- Keep mobile app notifications enabled
- Check battery optimization settings on mobile

### Performance

- Avoid sending too many notifications
- Use conditions to filter unnecessary alerts
- Set appropriate retry intervals

---

## Advanced Configuration

### Multiple Vehicles with Different Notifications

Configure unique notification settings per vehicle:

```yaml
# Vehicle 1 - Primary phone
ev_trip_planner:
  vehicles:
    - vehicle_id: tesla_model_3
      notification_service: notify.mobile_app_tesla_phone
      # ...

# Vehicle 2 - Work phone
    - vehicle_id: ioniq_5
      notification_service: notify.mobile_app_work_phone
      # ...
```

### Conditional Notification Routing

Route notifications based on trip urgency:

```yaml
automation:
  - alias: "EV - Urgent Trip Notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.ev_trip_planner_{vehicle_id}_charging_needed
        to: "on"
    condition:
      - condition: template
        value_template: >
          {% set trip = state_attr('sensor.ev_trip_planner_{vehicle_id}_next_trip', 'departure_time') %}
          {% set departure = strptime(trip, '%H:%M') if trip else none %}
          {% set now = now() %}
          {{ departure and (departure.hour - now.hour) < 2 }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚨 URGENT: EV Charging Needed!"
          message: "Trip departure in less than 2 hours!"
          data:
            priority: high
            sound: critical
```

---

## Quick Reference

### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `notification_service` | string | Notify service entity (e.g., `notify.mobile_app_phone`) |
| `notification_devices` | list | Specific device IDs to notify |

### Notification Events

| Event | Trigger |
|-------|---------|
| `ev_trip_planner_{vehicle_id}_charging_not_possible` | Charging needed but not possible |
| `ev_trip_planner_{vehicle_id}_vehicle_not_home` | Vehicle away from home |
| `ev_trip_planner_{vehicle_id}_vehicle_not_plugged` | Vehicle not connected to charger |
| `ev_trip_planner_{vehicle_id}_charging_failed` | All retries exhausted |

### Common Service Names

```
notify.mobile_app_iphone
notify.mobile_app_android
notify.mobile_app_your_device
notify.telegram
notify.email_gmail
notify.persistent_notification
```

---

## Additional Resources

- [Home Assistant Notify Integration](https://www.home-assistant.io/integrations/notify/)
- [Mobile App Notifications](https://companion.home-assistant.io/docs/notifications)
- [Vehicle Control Guide](VEHICLE_CONTROL.md)
- [EMHASS Integration Guide](EMHASS_INTEGRATION.md)
- [Dashboard Guide](DASHBOARD.md)
- [Configuration Examples](configuration_examples.yaml)
