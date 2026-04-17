# API Contracts: HA EV Trip Planner Services

> Generated: 2026-04-16 | Scan Level: Deep

## Overview

EV Trip Planner exposes 9+ Home Assistant services for trip management, vehicle control, and dashboard operations. All services are registered under the `ev_trip_planner` domain.

## Service Catalog

### Trip CRUD Services

#### `ev_trip_planner.add_recurring_trip`

Creates a recurring weekly trip.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier (e.g., "chispitas") |
| `dia_semana` | string | ✅ | Day of week in Spanish (lunes-domingo) |
| `hora` | string | ✅ | Time in HH:MM format |
| `km` | float | ✅ | Trip distance in kilometers |
| `kwh` | float | ✅ | Estimated energy in kWh |
| `descripcion` | string | ❌ | Trip description |

**Response**: Triggers coordinator refresh → sensor update

---

#### `ev_trip_planner.add_punctual_trip`

Creates a one-time trip.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `datetime` | string | ✅ | ISO datetime (e.g., "2025-11-19T15:00:00") |
| `km` | float | ✅ | Trip distance in kilometers |
| `kwh` | float | ✅ | Estimated energy in kWh |
| `descripcion` | string | ❌ | Trip description |

**Response**: Triggers coordinator refresh → sensor update

---

#### `ev_trip_planner.trip_create`

Unified trip creation service (recurring or punctual).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `type` | string | ✅ | "recurrente" or "puntual" |
| `dia_semana` | string | conditional | Day of week (required if type=recurrente) |
| `hora` | string | conditional | Time HH:MM (required if type=recurrente) |
| `datetime` | string | conditional | ISO datetime (required if type=puntual) |
| `km` | float | ✅ | Trip distance |
| `kwh` | float | ✅ | Estimated energy |
| `descripcion` | string | ❌ | Trip description |

**Response**: Returns created trip data via `SupportsResponse.ONLY`

---

#### `ev_trip_planner.edit_trip`

Edits an existing trip's fields.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `trip_id` | string | ✅ | Trip ID to edit (e.g., "rec_lun_abc12345") |
| `updates` | dict | ✅ | Dictionary of fields to update (e.g., `{"hora": "10:00"}`) |

**Editable fields**: `dia_semana`, `hora`, `km`, `kwh`, `descripcion`, `datetime`, `activo`

---

#### `ev_trip_planner.delete_trip`

Deletes a trip permanently.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `trip_id` | string | ✅ | Trip ID to delete |

---

### Trip State Services

#### `ev_trip_planner.pause_recurring_trip`

Pauses a recurring trip (marks as inactive).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `trip_id` | string | ✅ | Recurring trip ID |

---

#### `ev_trip_planner.resume_recurring_trip`

Resumes a paused recurring trip.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `trip_id` | string | ✅ | Recurring trip ID |

---

#### `ev_trip_planner.complete_punctual_trip`

Marks a punctual trip as completed.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |
| `trip_id` | string | ✅ | Punctual trip ID |

---

### Dashboard Service

#### `ev_trip_planner.import_dashboard`

Imports/refreshes the Lovelace dashboard for a vehicle.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle_id` | string | ✅ | Vehicle identifier |

---

## Sensor Data Contract

### Coordinator Data Structure

The `TripPlannerCoordinator` exposes the following data contract via `coordinator.data`:

```python
{
    # Trip collections
    "recurring_trips": dict[str, dict],      # trip_id → trip_data
    "punctual_trips": dict[str, dict],        # trip_id → trip_data

    # Today's aggregates
    "kwh_today": float,                       # Total kWh needed today
    "hours_today": float,                     # Total charging hours needed today
    "next_trip": dict | None,                 # Next upcoming trip details

    # EMHASS integration (populated when EMHASS configured)
    "emhass_power_profile": list | None,      # 168-hour binary power profile
    "emhass_deferrables_schedule": dict | None, # EMHASS schedule data
    "emhass_status": str | None,              # "ready" | "active" | "error" | None
}
```

### Trip Data Structure

```python
# Recurring Trip
{
    "id": "rec_lun_abc123",          # Trip ID (format: rec_{day}_{random})
    "type": "recurrente",             # Trip type
    "dia_semana": "lunes",            # Day of week (Spanish)
    "hora": "09:00",                  # Departure time (HH:MM)
    "km": 24.0,                       # Distance in km
    "kwh": 3.6,                       # Energy needed in kWh
    "descripcion": "Trabajo",         # Description
    "activo": True,                   # Active/paused state
    "emhass_index": 0,                # EMHASS deferrable load index
}

# Punctual Trip
{
    "id": "pun_20251119_abc123",      # Trip ID (format: pun_{date}_{random})
    "type": "puntual",                # Trip type
    "datetime": "2025-11-19T15:00:00", # ISO datetime
    "km": 110.0,                      # Distance in km
    "kwh": 16.5,                      # Energy needed in kWh
    "descripcion": "Viaje a Toledo",  # Description
    "completado": False,              # Completion state
    "emhass_index": 1,                # EMHASS deferrable load index
}
```

### Sensor Entities (per vehicle)

| Sensor Key | Type | Unit | Description |
|-----------|------|------|-------------|
| `recurring_trips_count` | measurement | - | Number of recurring trips |
| `punctual_trips_count` | measurement | - | Number of punctual trips |
| `trips_list` | - | - | List of all trip IDs |
| `kwh_needed_today` | total_increasing | kWh | Total energy needed today |
| `hours_needed_today` | measurement | h | Total charging hours needed |
| `next_trip` | - | - | Next trip ID |
| `next_trip_departure` | - | - | Next trip departure time |
| `power_profile` | - | - | 168-hour binary power profile |

### EMHASS Sensor Attributes (per trip)

| Attribute | Type | Description |
|-----------|------|-------------|
| `def_total_hours` | float | Total deferrable hours |
| `P_deferrable_nom` | float | Nominal deferrable power (W) |
| `def_start_timestep` | int | Start timestep in EMHASS schedule |
| `def_end_timestep` | int | End timestep in EMHASS schedule |
| `power_profile_watts` | list | Power profile in watts |
| `trip_id` | str | Associated trip ID |
| `emhass_index` | int | EMHASS deferrable load index |
| `kwh_needed` | float | Energy needed for trip |
| `deadline` | str | Trip deadline timestamp |

## Authentication

All services require Home Assistant authentication. No additional API keys are needed. Services are called via HA's standard service call mechanism (UI, automations, or REST API with bearer token).
