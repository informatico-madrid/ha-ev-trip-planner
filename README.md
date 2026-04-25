# 🚗⚡ EV Trip Planner for Home Assistant

**Plan electric trips and optimize your vehicle's energy consumption**

[![HACS](https://img.shields.io/badge/HACS-Default-orange?style=for-the-badge)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/version-0.5.20-blue?style=for-the-badge)](https://github.com/informatico-madrid/ha-ev-trip-planner/releases)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Built with Smart Ralph](https://img.shields.io/badge/Built%20with-Smart%20Ralph%20Fork-blueviolet?style=for-the-badge)](https://github.com/informatico-madrid/smart-ralph)

## 📋 Table of Contents

- [🎯 Features](#-features)
- [⚠️ Prerequisites](#️-prerequisites)
- [🚀 Installation](#-installation)
  - [Method 1: HACS (Recommended)](#method-1-hacs-recommended)
  - [Method 2: Manual Installation](#method-2-manual-installation)
  - [Method 3: Development/Testing](#method-3-developmenttesting)
- [⚙️ Initial Configuration](#️-initial-configuration)
- [🎮 Usage](#-usage)
- [🔄 Update](#-update)
- [🗑️ Uninstallation](#️-uninstallation)
- [🔧 Troubleshooting](#-troubleshooting)
- [📊 Development](#-development)
  - [🤖 Smart Ralph Methodology](#-smart-ralph-methodology)
- [📚 Documentación](#-documentación)

---

> 🧪 **This project is also an AI-assisted development laboratory.**
> How a senior architect led the generation of 12,000+ lines of functional code
> through specialized AI agents — [See Portfolio](_ai/PORTFOLIO.md)

---

## 🎯 Features

For the complete milestone history and project roadmap, see [ROADMAP.md](ROADMAP.md).

### Core Features
- **🗓️ Recurring and Punctual Trips**: Schedule daily/weekly trips or plan one-time trips with specific date/time
- **🔋 Smart Optimization**: Calculates required energy based on distance, efficiency, and current SOC
- **⚡ EMHASS Integration**: Energy optimization with dynamic schedules to take advantage of variable tariffs
- **🎮 Vehicle Control**: 4 strategies (switch, service, script, external) for charge control
- **🏠 Presence Detection**: Sensor and coordinates for safe charging
- **🔔 Smart Notifications**: Alerts when charging is needed but not possible
- **📱 Real-Time Sensors**: Automatic sensors with reactive updates
- **🎛️ Lovelace Dashboard**: Preconfigured panel included

---

## ⚠️ Prerequisites

### For End Users (Production)
- Home Assistant Core ≥ 2023.8.0 or Supervisor
- HACS (Home Assistant Community Store) installed
- "Advanced Mode" enabled in your HA profile
- **Optional**: EMHASS installed for energy optimization

### For Developers
- Python 3.14
- Git
- Docker (optional, for testing)
- Basic YAML and Linux command knowledge

---

## 🚀 Installation

### Method 1: HACS (Recommended) ⭐

**This is the method for end users. No terminal commands required.**

1. **Open Home Assistant** in your browser (`http://your-ip:8123`)

2. **Access HACS**:
   - Sidebar → HACS

3. **Add the custom repository**:
   - HACS → Integrations → ⋮ (menu) → Custom repositories
   - URL: `https://github.com/informatico-madrid/ha-ev-trip-planner`
   - Category: `Integration`
   - Click **ADD**

4. **Install the integration**:
   - Search for "EV Trip Planner" in HACS
   - Click on the component
   - Press **DOWNLOAD**

5. **Restart Home Assistant**:
   - Configuration → System → Restart
   - Wait 30-60 seconds

6. **Add the integration**:
   - Configuration → Devices and Services → + ADD INTEGRATION
   - Search for "EV Trip Planner"
   - Follow the configuration wizard

✅ **Done!** Sensors will be created automatically.

---

### Method 2: Manual Installation (Production)

**Use this method only if you don't have HACS or need a specific version.**

1. **Download the latest version** from the releases page:
   - Go to https://github.com/informatico-madrid/ha-ev-trip-planner/releases
   - Download the `.zip` file of the version you want

2. **Copy to Home Assistant directory**:
   ```bash
   cd /tmp
   unzip ha-ev-trip-planner-X.X.X.zip
   cp -r ha-ev-trip-planner-X.X.X/custom_components/ev_trip_planner \
     $HOME/homeassistant/custom_components/
   ```
   (Replace X.X.X with the downloaded version)

3. **Fix permissions**:
   ```bash
   chown -R 1000:1000 $HOME/homeassistant/custom_components/ev_trip_planner
   ```

4. **Restart Home Assistant**:
   ```bash
   docker restart homeassistant
   ```

5. **Add the integration** from the UI (step 6 from Method 1)

---

### Method 3: Development/Testing

**⚠️ ONLY for development. DO NOT use in production.**

1. **Clone the repository**:
   ```bash
   cd /your/projects/directory
   git clone https://github.com/informatico-madrid/ha-ev-trip-planner.git
   cd ha-ev-trip-planner
   ```

2. **Create symbolic link** (for hot-reload development):
   ```bash
   ln -sf /your/projects/directory/ha-ev-trip-planner/custom_components/ev_trip_planner \
     $HOME/homeassistant/custom_components/ev_trip_planner
   ```

3. **Install development dependencies**:
   ```bash
   cd ha-ev-trip-planner
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements_dev.txt
   ```

4. **Run tests**:
   ```bash
   pytest tests/ -v --cov=custom_components/ev_trip_planner
   ```

5. **Restart Home Assistant** and check logs:
   ```bash
   docker restart homeassistant && docker logs -f homeassistant
   ```

---

## ⚙️ Initial Configuration

### Basic Configuration (UI)

1. **After adding the integration**, the wizard will guide you through **5 steps**:

   - **Step 1 - Vehicle**: Vehicle name and SOC sensor
   - **Step 2 - Battery**: Capacity, charging power, consumption
   - **Step 3 - EMHASS** (optional): Energy optimization configuration
   - **Step 4 - Presence** (optional): Home and plug sensors
   - **Step 5 - Notifications**: Notification service and device

2. **Available translations**: The project includes Spanish (`es`) and English (`en`) translations. The interface displays in the language configured in your Home Assistant.

3. **Automatic dashboard**: Upon completing configuration, the system will attempt to import a preconfigured Lovelace dashboard.

4. **Sensors will be created automatically**, including:
   - `sensor.{vehicle}_trips_list` - List of active trips
   - `sensor.{vehicle}_next_trip` - Next trip
   - `sensor.{vehicle}_next_deadline` - Deadline for charging
   - `sensor.{vehicle}_kwh_today` - Required energy today
   - `sensor.emhass_perfil_diferible_{vehicle_id}` - EMHASS charging profile
   - Additional sensors based on configuration (presence, EMHASS deferrable, etc.)

### Advanced Configuration (YAML)

> ⚠️ **DEPRECATED**: The EV Trip Planner integration uses exclusively **config flow UI**.
> Configuration via `configuration.yaml` is not supported. This section is maintained only
> for historical reference.

<!--
```yaml
# configuration.yaml (NO LONGER SUPPORTED)
ev_trip_planner:
  vehicles:
    - name: "MyCar"
      battery_capacity_kwh: 27
      efficiency_kwh_km: 0.15
      min_soc: 20
```
-->

---

## 🎮 Usage

### Available Services

EV Trip Planner exposes the following services:

| Service | Description |
|---------|-------------|
| `ev_trip_planner.add_recurring_trip` | Creates a recurring trip (weekdays, fixed time) |
| `ev_trip_planner.add_punctual_trip` | Creates a punctual trip (specific date/time) |
| `ev_trip_planner.edit_trip` | Modifies an existing trip |
| `ev_trip_planner.delete_trip` | Deletes a trip |
| `ev_trip_planner.pause_recurring_trip` | Pauses a recurring trip |
| `ev_trip_planner.resume_recurring_trip` | Resumes a paused recurring trip |
| `ev_trip_planner.get_trips` | Gets the list of configured trips |

### Create a Recurring Trip (e.g., work)

1. **Developer Tools** → **Services**
2. **Service**: `ev_trip_planner.add_recurring_trip`
3. **Service data**:

```yaml
service: ev_trip_planner.add_recurring_trip
data:
  vehicle_id: "MyCar"
  dia_semana: "monday"
  hora: "08:00"
  km: 25
  kwh: 3.75
  descripcion: "Work"
```

### Create a Punctual Trip (e.g., airport)

```yaml
service: ev_trip_planner.add_punctual_trip
data:
  vehicle_id: "MyCar"
  datetime: "2025-12-15T14:30:00"
  km: 50
  kwh: 7.5
  descripcion: "Airport"
```

### View Trips on Dashboard

1. **Edit your** Lovelace dashboard
2. **Add a card** → **Entities**
3. **Select the vehicle sensors**

---

## ⚡ EMHASS Integration

### What is EMHASS?

**EMHASS** (Energy Management for Home Assistant) is an energy optimizer
that manages deferrable loads (like electric vehicle charging) to take advantage
of variable tariffs and renewable energy.

### EMHASS Configuration

When configuring your vehicle, you can configure these EMHASS parameters:

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| Planning Horizon | Planning days (1-365) | 7 days |
| Max Deferrable Loads | Simultaneous loads (10-100) | 50 |
| Planning Sensor | Horizon sensor (optional) | - |

### Deferrable Load Sensors

The system creates template sensors:

- `sensor.emhass_perfil_diferible_{vehicle_id}` - Aggregated power profile (168 values)
- `sensor.emhass_deferrable{N}_power` - Power profile by index (N = 0-49)
- `sensor.emhass_deferrable{N}_schedule` - Hourly detail with ISO 8601 timestamps

Aggregated sensor attributes:
- `power_profile_watts`: Array of 168 values (24h × 7d), 0 = no charge
- `deferrables_schedule`: Hourly detail
- `active_indices`: List of active indices

### Shell Command Example (ADVANCED)

For expert users using external EMHASS, add this to your `configuration.yaml`:

```yaml
shell_command:
  emhass_day_ahead_optim: >
    curl -i -H "Content-Type: application/json" -X POST -d '{
      "P_deferrable": {{ state_attr(
        'sensor.emhass_perfil_diferible_micar',
        'power_profile_watts'
      ) | default([0]*168, true) | tojson }}
    }' http://$EMHASS_IP:5000/action/dayahead-optim
```

**Note**: Replace `micar` with your vehicle ID. For multiple vehicles,
configure multiple shell commands, one per vehicle.

### Verify Integration

1. **Dashboard**: Go to the `ev-trip-planner-{vehicle_id}` dashboard
2. **Entities**: Search for `sensor.emhass_deferrable*` or `sensor.emhass_perfil_diferible*`
3. **Logs**: Look for "Published X/Y deferrable loads" to confirm successful publication

---

## 🚗 Vehicle Control

### Control Types

EV Trip Planner supports 4 control strategies:

| Type | Description | When to Use |
|------|-------------|-------------|
| **None** | No automatic control | Monitoring and notifications only |
| **Switch** | Direct ON/OFF control | Wallbox with switch entity |
| **Service** | HA service calls | Integrations that expose services |
| **Script** | Execute HA scripts | Customizable charging with complex logic |
| **External** | No internal action | Delegate everything to external system |

### Control Configuration

#### Switch (Recommended for wallboxes)

1. Select "Switch" as control type
2. Choose the charging switch (e.g., `switch.wallbox_charging`)
3. The system will turn the switch on/off according to EMHASS schedule

#### Service

1. Select "Service" as control type
2. Provide ON service (e.g., `switch.turn_on`) and OFF service (e.g., `switch.turn_off`)
3. Include service data if needed (target entity, parameters)

#### Script

1. Select "Script" as control type
2. Choose the start script (e.g., `script.start_charging`)
3. Choose the stop script (e.g., `script.stop_charging`)
4. The system will execute the appropriate script according to EMHASS schedule

#### External

1. Select "External" as control type
2. The integration will not execute any direct action
3. Useful when another system manages charging

### Presence Detection

For safe operation, the system verifies:

- **Charging sensor** (REQUIRED): Is the vehicle consuming energy?
- **Home sensor** (optional): Is the vehicle at the expected location?
- **Plug sensor** (optional): Is the charging cable connected?

### Complete Control Flow

```
EMHASS optimizes schedules → ScheduleMonitor receives callbacks
    → Verifies presence (presence_monitor)
    → Is vehicle available and needs charging?
        → Yes → VehicleController activates strategy (switch/service/script)
        → No → Sends notification (if configured)
```

---

## 🔄 Update

### Automatic Update (HACS)

1. **HACS** → **Integrations**
2. Search for "EV Trip Planner"
3. If an update is available, an **UPDATE** button will appear
4. Click it and **restart Home Assistant**

### Manual Update (from GitHub)

1. **Download the new version** from the releases page:
   - Go to https://github.com/informatico-madrid/ha-ev-trip-planner/releases

2. **Copy the files** overwriting existing ones

3. **Restart Home Assistant**

### Update from git (Developers)

If you installed from git clone:
```bash
cd /your/ha-ev-trip-planner/directory
git pull origin main
docker restart homeassistant
```

**⚠️ IMPORTANT**: Updates do not delete your trips. Data persists
in Home Assistant's Storage at `.storage/ev_trip_planner_{vehicle_id}`.

---

## 🗑️ Uninstallation

### Method 1: From HACS (Recommended)

1. **HACS** → **Integrations**
2. Search for "EV Trip Planner"
3. ⋮ (menu) → **Remove**
4. **Restart Home Assistant**

### Method 2: Manual

1. **Remove the integration**:
   - Configuration → Devices and Services
   - Search for "EV Trip Planner"
   - ⋮ → **Remove**

2. **Remove the files**:
   ```bash
   rm -rf $HOME/homeassistant/custom_components/ev_trip_planner
   ```

3. **Restart Home Assistant**

### ⚠️ Note About Trip Data

> **🐛 KNOWN BUG**: When uninstalling the integration, trip data
> saved in `.storage/` may not persist correctly between
> uninstallation and reinstallation. This is a known bug documented
> in the project roadmap.
>
> **Temporary mitigation**: Before uninstalling, export your trips using
> the service `ev_trip_planner.get_trips` to have a backup.
>
> **Fix in development**: The team is working on a solution to
> guarantee data persistence post-uninstallation.

### Complete Cleanup (Optional)

To permanently delete all data:

1. Stop Home Assistant
2. Delete data files:
   ```bash
   rm -f $HOME/homeassistant/.storage/ev_trip_planner_*.json
   ```
3. Delete any dashboard cards related to EV Trip Planner
4. Restart Home Assistant

---

## 🔧 Troubleshooting

### Sensors Don't Appear

1. **Check logs**:
   ```bash
   docker logs homeassistant --tail 50 | grep ev_trip_planner
   ```

2. **Verify the integration is loaded**:
   - Configuration → Devices and Services
   - Search for "EV Trip Planner"
   - You should see at least 1 device (configured vehicle)
   - Each active trip creates additional sensors

3. **Reinstall if necessary**

### Error: "Service Not Found"

- **Restart Home Assistant** (service is registered at startup)
- Verify the component is in `custom_components/`:
  ```bash
  ls -la $HOME/homeassistant/custom_components/ev_trip_planner/
  ```

### Trips Don't Save

- **Trips persist between restarts** using Home Assistant's Storage API
- **Check permissions**:
  ```bash
  ls -la $HOME/homeassistant/.storage/ | grep ev_trip_planner
  ```
- Files are saved in `.storage/ev_trip_planner_{vehicle_id}.json`

### Dashboard Doesn't Import

- **Verify Lovelace is available**: The system needs Lovelace to be configured
- The dashboard is created during the configuration flow, not after restart
- If the dashboard doesn't appear, go to Configuration → Lovelace Dashboard → + (add)
  and search for "EV Trip Planner" in the available dashboards list

### EMHASS Issues

1. **Verify EMHASS is running**:
   ```bash
   curl http://$EMHASS_IP:5000/action/dayahead-optim
   ```

2. **Verify EMHASS configuration**:
   - EMHASS's `config.json` must have sufficient `number_of_deferrable_loads`
   - If you configured more trips than available slots, trips won't appear in EMHASS

---

## 📊 Development

### 🤖 Smart Ralph Methodology

This plugin was developed with **[`informatico-madrid/smart-ralph`](https://github.com/informatico-madrid/smart-ralph)**,
a fork of [tzachbon/smart-ralph](https://github.com/tzachbon/smart-ralph) that implements
a spec-driven development loop with specialized AI agents in parallel reviewing
and executing each spec.

Every feature, fix, or refactor went through a complete cycle:
`Research → Requirements → Design → Tasks → Implement → Agentic Verification`

The project was deliberately the test laboratory for the plugin itself — and at the same time
resulted in a functional component in production. Over 20 specs generated throughout
development are in `specs/`.

→ **[See complete methodology](_ai/RALPH_METHODOLOGY.md)**

---

The complete E2E testing guide is at [_ai/TESTING_E2E.md](_ai/TESTING_E2E.md).

### Project Structure

```
ha-ev-trip-planner/
├── custom_components/ev_trip_planner/
│   ├── __init__.py          # Entry point and setup
│   ├── config_flow.py       # UI Configuration (5 steps)
│   ├── const.py             # Constants
│   ├── sensor.py            # Sensor entities
│   ├── trip_manager.py      # Core trip logic
│   ├── services.py          # Service handlers
│   ├── services.yaml        # YAML service definition
│   ├── emhass_adapter.py    # EMHASS integration
│   ├── vehicle_controller.py # Vehicle control (switch/service/script)
│   ├── presence_monitor.py   # Presence monitoring
│   ├── schedule_monitor.py  # EMHASS schedule monitoring
│   ├── dashboard.py          # Automatic dashboard import
│   ├── coordinator.py        # Data coordinator
│   ├── calculations.py      # Charge calculations
│   ├── utils.py             # Utilities
│   ├── yaml_trip_storage.py # Optional YAML storage
│   ├── definitions.py       # Entity definitions
│   ├── diagnostics.py       # HA diagnostics support
│   ├── panel.py             # Custom UI panel
│   └── translations/        # Translations (en.json, es.json)
├── frontend/                # Lovelace Panel (Lit web components)
│   ├── panel.js
│   └── panel.css
├── dashboard/               # Predefined Dashboard YAMLs
├── tests/                   # Unit and integration tests
│   ├── test_*.py            # ~85 test files
│   └── e2e/                  # E2E Tests (Playwright)
│       ├── create-trip.spec.ts
│       ├── delete-trip.spec.ts
│       └── ...
├── specs/                   # Smart Ralph specs history
├── docs/                    # User/developer documentation
│   ├── index.md            # Documentation index
│   ├── architecture.md     # System architecture
│   ├── api-contracts.md    # API contracts
│   ├── data-models.md      # Data models
│   ├── development-guide.md # Development guide
│   └── *.md                # Other documentation
├── _ai/                     # AI agent documentation (dense/technical)
│   ├── index.md           # AI documentation index
│   ├── RALPH_METHODOLOGY.md # Smart Ralph methodology
│   ├── TESTING_E2E.md      # E2E testing guide
│   ├── PORTFOLIO.md        # Project portfolio
│   └── *.md                # Technical guides for AI agents
├── plans/                   # Active development plans
├── _roo/skills/             # Roo agent skills
├── .agents/skills/          # BMad agent skills
├── .github/workflows/       # CI/CD
├── hacs.json                # HACS metadata
├── manifest.json            # HA metadata
└── README.md               # This file
```

### Run Tests

**Unit and integration tests:**
```bash
cd /your/ha-ev-trip-planner/directory
source venv/bin/activate
pytest tests/ -v --cov=custom_components/ev_trip_planner
```

**Specific file tests:**
```bash
pytest tests/test_trip_manager.py -v
pytest tests/test_emhass_adapter.py -v
```

**E2E Tests (requires Playwright):**
```bash
cd /your/ha-ev-trip-planner/directory
npx playwright test tests/e2e/
```

**See E2E documentation:**
→ **[Complete E2E testing guide](_ai/TESTING_E2E.md)**

### Contributing

1. **Fork the repository**
2. **Create a branch**: `git checkout -b feature/new-feature`
3. **Make commits**: `git commit -am 'Adds new feature'`
4. **Push**: `git push origin feature/new-feature`
5. **Create a Pull Request**

---

## 📚 Documentación

| Documentación | Descripción |
|---------------|-------------|
| [📖 docs/index.md](docs/index.md) | Documentación para usuarios y desarrolladores |
| [🤖 _ai/index.md](_ai/index.md) | Documentación técnica para agentes IA |
| [📋 plans/DOCS_AUDIT_REPORT.md](plans/DOCS_AUDIT_REPORT.md) | Informe completo de auditoría de documentación |

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/informatico-madrid/ha-ev-trip-planner/discussions)
- **Documentation**: [Wiki](https://github.com/informatico-madrid/ha-ev-trip-planner/wiki)

---

**⭐ If you like this component, give it a star on GitHub!**
