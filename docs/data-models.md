# Data Models: HA EV Trip Planner

> Generated: 2026-04-16 | Scan Level: Deep

## Overview

EV Trip Planner uses Home Assistant's Store API for persistence and HA's entity registry for sensor management. There is no traditional database — all data is stored as JSON via HA's storage layer.

## Storage Architecture

### Store Keys

| Store Key | Version | Purpose |
|-----------|---------|---------|
| `ev_trip_planner_{vehicle_id}_trips` | 1 | Trip data (recurring + punctual) |
| `ev_trip_planner_{vehicle_id}_emhass_indices` | 1 | Trip ID → EMHASS index mapping |
| `ev_trip_planner_{vehicle_id}_presence` | 1 | Presence detection state |

## Core Data Models

### Trip Models

#### Recurring Trip

```python
{
    "id": "rec_lun_abc123",          # Format: rec_{day_abbrev}_{random_6char}
    "type": "recurrente",             # Literal["recurrente", "puntual"]
    "dia_semana": "lunes",            # Spanish day name (lunes-domingo)
    "hora": "09:00",                  # HH:MM format, validated by validate_hora()
    "km": 24.0,                       # Distance in kilometers (float)
    "kwh": 3.6,                       # Energy in kWh (calculated or manual)
    "descripcion": "Trabajo",         # Free text description
    "activo": True,                   # Active/paused toggle
    "emhass_index": 0,                # EMHASS deferrable load index (0-based)
    "vehicle_id": "chispitas",        # Vehicle identifier
}
```

**ID Generation**: `rec_{day_abbrev}_{6_random_chars}` (e.g., `rec_lun_abc123`)
- Day abbreviations: lun, mar, mie, jue, vie, sab, dom

#### Punctual Trip

```python
{
    "id": "pun_20251119_abc123",      # Format: pun_{YYYYMMDD}_{random_6char}
    "type": "puntual",
    "datetime": "2025-11-19T15:00:00", # ISO 8601 datetime
    "km": 110.0,
    "kwh": 16.5,
    "descripcion": "Viaje a Toledo",
    "completado": False,               # Completion flag
    "emhass_index": 1,
    "vehicle_id": "chispitas",
}
```

**ID Generation**: `pun_{YYYYMMDD}_{6_random_chars}` (e.g., `pun_20251119_abc123`)

### Trip Storage Schema

```python
# Store: ev_trip_planner_{vehicle_id}_trips
{
    "recurring_trips": {
        "rec_lun_abc123": { ... },     # trip_id → RecurringTrip
        "rec_mar_def456": { ... },
    },
    "punctual_trips": {
        "pun_20251119_abc123": { ... }, # trip_id → PunctualTrip
    }
}
```

### EMHASS Index Mapping

```python
# Store: ev_trip_planner_{vehicle_id}_emhass_indices
{
    "rec_lun_abc123": 0,               # trip_id → emhass_index
    "pun_20251119_abc123": 1,
    "_soft_deleted": {                   # Soft-deleted indices with cooldown
        "2": "2026-04-16T10:00:00Z",    # index → deletion_timestamp
    }
}
```

**Soft Delete**: Indices are soft-deleted with a 24-hour cooldown before reuse, preventing EMHASS conflicts during the same optimization cycle.

## TypedDict Models

### CargaVentana (Charging Window)

```python
class CargaVentana(TypedDict):
    ventana_horas: float          # Available charging window in hours
    kwh_necesarios: float        # Energy needed in kWh
    horas_carga_necesarias: float # Required charging hours
    inicio_ventana: Optional[datetime]  # Window start time
    fin_ventana: Optional[datetime]     # Window end time
    es_suficiente: bool           # Whether window is long enough
```

### SOCMilestoneResult (SOC Milestone)

```python
class SOCMilestoneResult(TypedDict):
    trip_id: str                  # Associated trip ID
    soc_objetivo: float           # Target SOC percentage
    kwh_necesarios: float        # Energy needed in kWh
    deficit_acumulado: float      # Accumulated deficit from backward propagation
    ventana_carga: CargaVentana   # Associated charging window
```

## Config Entry Data

### Vehicle Configuration (ConfigEntry.data)

```python
{
    # Step 1: Vehicle Info
    "vehicle_name": "Chispitas",            # Display name

    # Step 2: Battery & Sensors
    "battery_capacity_kwh": 60.0,           # Battery capacity in kWh
    "charging_power_kw": 11.0,              # Max charging power in kW
    "kwh_per_km": 0.15,                     # Energy consumption rate
    "safety_margin_percent": 10,            # Safety margin percentage
    "soc_sensor": "sensor.chispitas_soc",   # SOC sensor entity_id (optional)
    "range_sensor": "sensor.chispitas_range", # Range sensor (optional)
    "charging_status_sensor": "binary_sensor.chispitas_charging", # (optional)

    # Step 3: EMHASS (optional)
    "max_deferrable_loads": 50,             # Max EMHASS deferrable loads
    "index_cooldown_hours": 24,             # Soft-delete cooldown
    "planning_horizon_days": 7,             # Planning window
    "planning_sensor_entity": "sensor.emhass_planning", # (optional)

    # Step 4: Presence (optional)
    "home_sensor": "binary_sensor.chispitas_home",
    "plugged_sensor": "binary_sensor.chispitas_plugged",
    "charging_sensor": "binary_sensor.chispitas_charging",
    "home_coordinates": "40.4168,-3.7038",  # Lat,Lon string
    "vehicle_coordinates_sensor": "sensor.chispitas_location",

    # Notifications
    "notification_service": "persistent_notification.create",
    "notification_devices": "mobile_phone_1",
    "control_type": "switch",               # none|switch|service|script|external
}
```

**Config Version**: 2 (with migration from v1: `battery_capacity` → `battery_capacity_kwh`)

## Runtime Data Model

### EVTripRuntimeData

```python
@dataclass
class EVTripRuntimeData:
    coordinator: Any                                          # TripPlannerCoordinator
    trip_manager: TripManager | None = None
    sensor_async_add_entities: Callable | None = None
    emhass_adapter: Any = None
```

### Coordinator Data Contract

```python
coordinator.data = {
    "recurring_trips": dict[str, dict],        # All recurring trips
    "punctual_trips": dict[str, dict],          # All punctual trips
    "kwh_today": float,                         # Total kWh needed today
    "hours_today": float,                       # Total charging hours today
    "next_trip": dict | None,                   # Next upcoming trip
    "emhass_power_profile": list | None,        # 168-hour binary profile
    "emhass_deferrables_schedule": dict | None, # EMHASS schedule
    "emhass_status": str | None,                # "ready"|"active"|"error"|None
}
```

## Entity Registry

### Sensor Unique IDs

Pattern: `ev_trip_planner_{vehicle_id}_{sensor_key}`

| Sensor | Unique ID Example |
|--------|------------------|
| Recurring trips count | `ev_trip_planner_chispitas_recurring_trips_count` |
| Punctual trips count | `ev_trip_planner_chispitas_punctual_trips_count` |
| kWh needed today | `ev_trip_planner_chispitas_kwh_needed_today` |
| Hours needed today | `ev_trip_planner_chispitas_hours_needed_today` |
| Next trip | `ev_trip_planner_chispitas_next_trip` |
| Power profile | `ev_trip_planner_chispitas_power_profile` |
| EMHASS trip sensor | `ev_trip_planner_chispitas_emhass_{trip_id}` |

### Migration Pattern

v1 → v2: Unique IDs migrated from `ev_trip_planner_{key}` to `ev_trip_planner_{vehicle_id}_{key}` to support multi-vehicle.

## Presence Data

### Presence State

```python
{
    "is_home": True,                          # Vehicle at home
    "is_plugged": True,                       # Vehicle plugged in
    "is_charging": False,                     # Vehicle actively charging
    "last_soc": 65.0,                         # Last known SOC
    "last_seen_home": "2026-04-16T10:00:00Z", # Last home detection
    "distance_from_home": 15.5,               # Distance in meters
}
```

### Distance Calculation

Uses Haversine formula with 30m threshold for home detection:
```python
HOME_DISTANCE_THRESHOLD_METERS = 30.0
```

## Localization Models

### Translation Structure (strings.json)

```json
{
    "config": {
        "step": {
            "user": { "title": "Configure Vehicle" },
            "sensors": { "title": "Sensor Configuration" },
            "emhass": { "title": "EMHASS Integration" },
            "presence": { "title": "Presence Detection" }
        }
    },
    "options": {
        "step": { ... }
    }
}
```

Languages: `en` (English), `es` (Spanish)
