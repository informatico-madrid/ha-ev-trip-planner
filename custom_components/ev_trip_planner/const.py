"""Constants for the EV Trip Planner integration.

This module defines all configuration keys, default values, and enum constants
used by the EV Trip Planner custom component. Key dependencies:
- Home Assistant core (for sensor/entity management)
- EMHASS integration (for energy-aware trip planning)
- Spanish-language localization (via DAYS_OF_WEEK array)

Note: All CONF_* keys are used in the config flow and entity configuration.
Default values are optimized for typical EV/PHEV usage patterns.
"""

from typing import Any, Literal, Protocol

DOMAIN = "ev_trip_planner"

# Config entry version for migrations
CONFIG_VERSION = 3

# Dispatcher signal for reactive updates
SIGNAL_TRIPS_UPDATED = "ev_trip_planner_trips_updated"

# Configuration keys
CONF_VEHICLE_NAME = "vehicle_name"
CONF_SOC_SENSOR = "soc_sensor"
CONF_BATTERY_CAPACITY = "battery_capacity_kwh"
CONF_CHARGING_POWER = "charging_power_kw"
CONF_CONSUMPTION = "kwh_per_km"
CONF_SAFETY_MARGIN = "safety_margin_percent"

# Optional configuration
CONF_RANGE_SENSOR = "range_sensor"
CONF_CHARGING_STATUS = "charging_status_sensor"
CONF_CONTROL_TYPE = "control_type"

# EMHASS Integration (Milestone 3)
CONF_MAX_DEFERRABLE_LOADS = "max_deferrable_loads"
CONF_INDEX_COOLDOWN_HOURS = "index_cooldown_hours"
CONF_PLANNING_HORIZON = "planning_horizon_days"
CONF_PLANNING_SENSOR = "planning_sensor_entity"

# Presence Detection
CONF_HOME_SENSOR = "home_sensor"
CONF_PLUGGED_SENSOR = "plugged_sensor"
CONF_CHARGING_SENSOR = "charging_sensor"
CONF_HOME_COORDINATES = "home_coordinates"
CONF_VEHICLE_COORDINATES_SENSOR = "vehicle_coordinates_sensor"

# Notifications
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_NOTIFICATION_DEVICES = "notification_devices"

# Control types
CONTROL_TYPE_NONE = "none"
CONTROL_TYPE_SWITCH = "switch"
CONTROL_TYPE_SERVICE = "service"
CONTROL_TYPE_SCRIPT = "script"
CONTROL_TYPE_EXTERNAL = "external"

# Defaults
# These are form display defaults ONLY. Never use as runtime fallbacks.
DEFAULT_CONSUMPTION = 0.15  # kWh per km (typical EV efficiency)
DEFAULT_CHARGING_POWER = 11.0  # kW (typical home charger)
DEFAULT_SAFETY_MARGIN = 10  # percent (prevents depletion during unplanned stops)
DEFAULT_BATTERY_CAPACITY_KWH = 50.0  # kWh (typical EV battery capacity)
DEFAULT_SOC_BUFFER_PERCENT = (
    10  # percent (minimum SOC buffer for backward deficit propagation)
)
DEFAULT_CONTROL_TYPE = CONTROL_TYPE_NONE
DEFAULT_PLANNING_HORIZON = 7  # days (standard weekly planning window)
DEFAULT_MAX_DEFERRABLE_LOADS = 50  # Max simultaneous trips (EMHASS limit)
DEFAULT_INDEX_COOLDOWN_HOURS = 24  # hours (soft delete cooldown before index reuse)
DEFAULT_NOTIFICATION_SERVICE = "persistent_notification.create"

# Battery health / Dynamic SOC capping (always-on)
CONF_T_BASE = "t_base"
CONF_SOC_BASE = "soc_base"
CONF_SOH_SENSOR = "soh_sensor"
DEFAULT_T_BASE = 24.0  # hours (user-configurable via slider)
DEFAULT_SOC_BASE = 35.0  # percent (NMC/NCA chemistry sweet spot, internal-only)
MIN_T_BASE = 6.0  # hours (minimum slider value)
MAX_T_BASE = 48.0  # hours (maximum slider value)
DEFAULT_SOH_SENSOR = ""  # empty = use nominal capacity

# Fixed buffer between sequential trip charging windows (hours)
RETURN_BUFFER_HOURS = 4.0

# Trip types
TripType = Literal["recurrente", "puntual"]
TRIP_TYPE_RECURRING: TripType = "recurrente"
TRIP_TYPE_PUNCTUAL: TripType = "puntual"

# EMHASS states
EMHASS_STATE_READY = "ready"
EMHASS_STATE_ACTIVE = "active"
EMHASS_STATE_ERROR = "error"

# Trip status (for punctual trips)
TRIP_STATUS_PENDING = "pendiente"
TRIP_STATUS_COMPLETED = "completado"
TRIP_STATUS_CANCELLED = "cancelado"

# Days of week (Spanish as base for localization)
DAYS_OF_WEEK = [
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
]

# TripEmhassSensor documented attribute keys
# Prevents data leak of internal cache keys (activo, *_array, p_deferrable_matrix, etc.)
TRIP_EMHASS_ATTR_KEYS: frozenset[str] = frozenset({
    "def_total_hours",
    "P_deferrable_nom",
    "def_start_timestep",
    "def_end_timestep",
    "power_profile_watts",
    "trip_id",
    "emhass_index",
    "kwh_needed",
    "deadline",
})


class ConfigEntryProtocol(Protocol):
    """Protocol for Home Assistant config entries."""

    entry_id: str
    data: dict[str, Any]
