# Architecture Documentation: HA EV Trip Planner

> Generated: 2026-04-16 | Scan Level: Deep

## Executive Summary

HA EV Trip Planner is a Home Assistant custom component implementing the **DataUpdateCoordinator pattern** with a layered architecture. The system manages EV trip planning, charging optimization, and EMHASS energy integration through a clean separation of concerns: pure calculations, async orchestration, HA framework integration, and a Lit-based frontend panel.

## Technology Stack

### Backend (Python)

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ (target 3.14) | Core language |
| Home Assistant Framework | 2026.3.3+ | Integration platform |
| voluptuous | (HA bundled) | Config flow validation |
| PyYAML | (HA bundled) | Dashboard YAML parsing |
| pytest | Latest | Unit testing |
| ruff | Latest | Linting |
| pylint | Latest | Code analysis |
| mypy | Latest (strict) | Type checking |
| black | Latest | Code formatting |
| isort | Latest | Import sorting |

### Frontend (TypeScript/JavaScript)

| Technology | Version | Purpose |
|-----------|---------|---------|
| Lit | 2.8.x | Web Component framework |
| TypeScript | 5.7+ | Type-safe JS |
| Playwright | 1.58+ | E2E testing |
| Jest | 30.x | JS unit testing |

### Infrastructure

| Technology | Purpose |
|-----------|---------|
| Docker (docker-compose) | HA Container test environment |
| HACS | Community distribution |
| Make | Build automation |

## Architecture Pattern

### Layered Architecture with Coordinator Pattern

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Native Panel │  │  Lovelace    │  │  HA Sensors   │  │
│  │  (Lit/JS)     │  │  Dashboards  │  │  (7+ per veh) │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
├─────────┼─────────────────┼──────────────────┼───────────┤
│         │         Service Layer (HA Services) │           │
│  ┌──────┴─────────────────┴──────────────────┴───────┐   │
│  │              services.py (9+ services)             │   │
│  │  trip_create | trip_edit | trip_delete | ...       │   │
│  └──────────────────────┬────────────────────────────┘   │
├─────────────────────────┼────────────────────────────────┤
│                 Orchestration Layer                       │
│  ┌──────────────────────┴────────────────────────────┐   │
│  │           TripPlannerCoordinator                   │   │
│  │  (DataUpdateCoordinator - 30s polling cycle)       │   │
│  └──────┬────────────┬──────────────┬────────────────┘   │
│         │            │              │                      │
│  ┌──────┴──────┐ ┌───┴──────┐ ┌────┴──────────┐         │
│  │ TripManager │ │ EMHASS   │ │ Presence      │         │
│  │ (Core CRUD  │ │ Adapter  │ │ Monitor       │         │
│  │  + calc)    │ │ (Energy  │ │ (GPS + sensor)│         │
│  └──────┬──────┘ │ optim)   │ └───────────────┘         │
│         │        └────┬─────┘                            │
├─────────┼─────────────┼──────────────────────────────────┤
│              Calculation Layer (Pure Functions)           │
│  ┌──────┴─────────────┴──────────────────────────────┐   │
│  │              calculations.py                        │   │
│  │  calculate_trip_time | calculate_power_profile      │   │
│  │  calculate_charging_windows | calculate_soc_milestones│  │
│  │  generate_deferrable_schedule | calculate_day_index  │   │
│  └────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│              Infrastructure Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ HA Store     │  │ Vehicle      │  │ Schedule      │  │
│  │ (Trip data)  │  │ Controller   │  │ Monitor       │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Component Overview

### Core Components

#### 1. `__init__.py` — Integration Lifecycle
- **Entry point**: `async_setup_entry` / `async_unload_entry`
- Creates `TripManager`, `EMHASSAdapter`, `TripPlannerCoordinator`
- Registers panel, services, dashboard, presence monitor
- Manages `EVTripRuntimeData` per config entry
- Handles config entry migration (v1 → v2)

#### 2. `trip_manager.py` — Core Business Logic (1998 LOC)
- Trip CRUD operations (recurring + punctual)
- Energy calculation delegation to `calculations.py`
- EMHASS synchronization via `EMHASSPublisherProtocol`
- HA Store persistence for trip data
- SOC milestone calculations
- Charging window calculations

#### 3. `coordinator.py` — Data Update Coordinator
- Extends HA's `DataUpdateCoordinator`
- 30-second update interval
- Aggregates data from TripManager + EMHASSAdapter
- Exposes unified data contract for all sensors

#### 4. `calculations.py` — Pure Functions (1122 LOC)
- 100% synchronous, no HA dependencies
- All datetime functions take explicit `reference_dt` parameter
- Key functions:
  - `calculate_trip_time` — Trip datetime resolution
  - `calculate_power_profile_from_trips` — 168-hour binary charging profile
  - `calculate_multi_trip_charging_windows` — Charging window analysis
  - `calculate_deferrable_parameters` — EMHASS deferrable load params
  - `generate_deferrable_schedule_from_trips` — EMHASS schedule generation

#### 5. `emhass_adapter.py` — EMHASS Integration (1828 LOC)
- Publishes trips as EMHASS deferrable loads
- Manages trip_id → emhass_index mapping (HA Store)
- Power profile generation (binary: 0W or max power)
- SOC-aware charging optimization
- Soft-delete with cooldown for index reuse
- Notification dispatch for charging alerts

#### 6. `sensor.py` — Sensor Entities (908 LOC)
- `TripPlannerSensor` — Base sensor using CoordinatorEntity + RestoreSensor
- `TripEmhassSensor` — Per-trip EMHASS sensor (9 attributes)
- Dynamic sensor creation based on trip data
- Entity registry management (unique_id migration)

#### 7. `config_flow.py` — Configuration Flow (949 LOC)
- 4-step setup wizard:
  1. Vehicle name
  2. Battery/sensor configuration
  3. EMHASS integration (optional)
  4. Presence detection (optional)
- Options flow for reconfiguration
- Entity selector for sensor picking

#### 8. `services.py` — Service Handlers (1537 LOC)
- 9+ HA services:
  - `add_recurring_trip`, `add_punctual_trip`
  - `trip_create` (unified), `edit_trip`, `delete_trip`
  - `pause_recurring_trip`, `resume_recurring_trip`
  - `complete_punctual_trip`
  - `import_dashboard`
- Thin facade pattern — delegates to TripManager

#### 9. `vehicle_controller.py` — Charging Control (509 LOC)
- Strategy pattern with 4 implementations:
  - `SwitchStrategy` — Toggle HA switch entity
  - `ServiceStrategy` — Call HA service
  - `ScriptStrategy` — Run HA script
  - `ExternalStrategy` — No-op (external control)
- Retry mechanism with `RetryState` (3 attempts / 5 min window)

#### 10. `presence_monitor.py` — Presence Detection (769 LOC)
- Dual detection: sensor-based + GPS coordinate-based
- Haversine distance calculation (30m threshold)
- SOC tracking via sensor state changes
- Home/away event detection

#### 11. `schedule_monitor.py` — Schedule Monitoring (323 LOC)
- Monitors EMHASS schedule sensor state changes
- Triggers vehicle control when charging window starts
- Per-vehicle monitoring with `VehicleScheduleMonitor`

#### 12. `panel.py` — Native Panel (244 LOC)
- Registers custom sidebar panel via `panel_custom`
- Serves Lit web component from `frontend/panel.js`
- Cache-busting for JS updates

#### 13. `dashboard.py` — Dashboard Auto-Deploy (1261 LOC)
- Supports both storage mode (Supervisor) and YAML mode (Container)
- Auto-generates Lovelace dashboard from templates
- CRUD views for trip management
- Input helper creation for dashboard interactivity

### Supporting Components

| Component | File | Purpose |
|-----------|------|---------|
| `const.py` | Constants | Config keys, defaults, enums, trip types |
| `definitions.py` | Sensor definitions | `TripSensorEntityDescription` + `TRIP_SENSORS` tuple |
| `protocols.py` | Protocol interfaces | `TripStorageProtocol`, `EMHASSPublisherProtocol` |
| `utils.py` | Utilities | Trip ID generation, validation, sanitization |
| `diagnostics.py` | HA diagnostics | Debug information for HA support |
| `yaml_trip_storage.py` | YAML storage | Fallback storage for Container installs |

## Data Flow

### Trip Creation Flow
```
User → Panel/Service → services.py → TripManager.async_add_*()
  → Store.async_save() → coordinator.async_refresh_trips()
  → EMHASSAdapter.async_publish_deferrable_load()
  → Sensors update via CoordinatorEntity
```

### Data Update Cycle (every 30s)
```
TripPlannerCoordinator._async_update_data()
  → TripManager.get_recurring_trips()
  → TripManager.get_punctual_trips()
  → TripManager.calculate_today_stats()
  → EMHASSAdapter.get_status()
  → coordinator.data = unified dict
  → All sensors auto-update
```

## Design Patterns

| Pattern | Usage |
|---------|-------|
| **Coordinator** | DataUpdateCoordinator for sensor data polling |
| **Strategy** | Vehicle control strategies (4 implementations) |
| **Protocol (DI)** | `TripStorageProtocol`, `EMHASSPublisherProtocol` for testability |
| **Facade** | `services.py` as thin facade over TripManager |
| **Observer** | `async_track_state_change_event` for sensor monitoring |
| **Template Method** | Config flow with defined steps |
| **Adapter** | `EMHASSAdapter` wrapping EMHASS integration |
| **Entity Description** | `TripSensorEntityDescription` for declarative sensor definitions |

## Testing Strategy

| Layer | Tool | Coverage |
|-------|------|----------|
| Pure calculations | pytest + parametrize | 100% target |
| Trip manager | pytest + mocks | High |
| Coordinator | pytest + hass fixtures | High |
| Sensors | pytest + entity fixtures | High |
| Services | pytest + service mocks | High |
| Config flow | pytest + flow fixtures | High |
| E2E | Playwright | Critical paths |
| JS Panel | Jest | Panel logic |

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│         Home Assistant Container         │
│  ┌─────────────────────────────────────┐ │
│  │  custom_components/ev_trip_planner/ │ │
│  │  ├── Backend (Python)               │ │
│  │  ├── Frontend (panel.js)            │ │
│  │  └── Dashboard templates (YAML)     │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────────┐   │
│  │ EMHASS       │  │ Vehicle Sensors  │   │
│  │ (optional)   │  │ (SOC, range...)  │   │
│  └─────────────┘  └──────────────────┘   │
└─────────────────────────────────────────┘
```

- **Installation**: HACS (recommended) or manual
- **Container**: No Supervisor — uses YAML dashboard fallback
- **Storage**: HA Store API for trip data and EMHASS indices
