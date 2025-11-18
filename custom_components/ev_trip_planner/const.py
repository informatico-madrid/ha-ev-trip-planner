"""Constants for the EV Trip Planner integration."""

DOMAIN = "ev_trip_planner"

# Dispatcher signal for reactive updates
SIGNAL_TRIPS_UPDATED = "ev_trip_planner_trips_updated"

# Configuration keys
CONF_VEHICLE_NAME = "vehicle_name"
CONF_VEHICLE_TYPE = "vehicle_type"
CONF_SOC_SENSOR = "soc_sensor"
CONF_BATTERY_CAPACITY = "battery_capacity_kwh"
CONF_CHARGING_POWER = "charging_power_kw"
CONF_CONSUMPTION = "kwh_per_km"
CONF_SAFETY_MARGIN = "safety_margin_percent"

# Optional configuration
CONF_RANGE_SENSOR = "range_sensor"
CONF_CHARGING_STATUS = "charging_status_sensor"
CONF_CONTROL_TYPE = "control_type"

# Control types
CONTROL_TYPE_NONE = "none"
CONTROL_TYPE_SWITCH = "switch"
CONTROL_TYPE_SERVICE = "service"
CONTROL_TYPE_EXTERNAL = "external"

# Vehicle types
VEHICLE_TYPE_EV = "ev"
VEHICLE_TYPE_PHEV = "phev"

# Defaults
DEFAULT_CONSUMPTION = 0.15  # kWh per km
DEFAULT_SAFETY_MARGIN = 10  # percent
DEFAULT_CONTROL_TYPE = CONTROL_TYPE_NONE
DEFAULT_VEHICLE_TYPE = VEHICLE_TYPE_EV

# Trip types
TRIP_TYPE_RECURRING = "recurrente"
TRIP_TYPE_PUNCTUAL = "puntual"
# Trip status (for punctual trips)
TRIP_STATUS_PENDING = "pendiente"
TRIP_STATUS_COMPLETED = "completado"
TRIP_STATUS_CANCELLED = "cancelado"


# Trip status
TRIP_STATUS_PENDING = "pendiente"
TRIP_STATUS_COMPLETED = "completado"
TRIP_STATUS_CANCELLED = "cancelado"

# Days of week (Spanish as base, will translate)
DAYS_OF_WEEK = [
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
]
