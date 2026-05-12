"""Sensor package for EV Trip Planner.

Re-exports all public names from the legacy sensor.py module.

During the SOLID decomposition, the legacy sensor.py module file
is replaced by a sensor/ package directory. This __init__.py
re-exports every public name so that existing import paths continue
to work without changes.
"""

from __future__ import annotations

# Entity classes from sub-modules.
from .entity_emhass_deferrable import EmhassDeferrableLoadSensor
from .entity_trip import TripSensor
from .entity_trip_emhass import TripEmhassSensor
from .entity_trip_planner import TripPlannerSensor

# Platform entry point and helpers from the legacy module.
from custom_components.ev_trip_planner.sensor_orig import (
    TRIP_SENSORS,
    async_create_trip_emhass_sensor,
    async_create_trip_sensor,
    async_remove_trip_emhass_sensor,
    async_remove_trip_sensor,
    async_setup_entry,
    async_update_trip_sensor,
)

# Internal helpers (needed for test mocking).
from custom_components.ev_trip_planner.sensor_orig import (
    _async_create_trip_sensors,  # noqa: F401
)

# Legacy module reference (for backwards-compatible test mocking).
import custom_components.ev_trip_planner.sensor_orig as sensor_orig  # noqa: F401

__all__ = [
    "TRIP_SENSORS",
    "async_setup_entry",
    "TripPlannerSensor",
    "EmhassDeferrableLoadSensor",
    "TripSensor",
    "TripEmhassSensor",
    "async_create_trip_sensor",
    "async_update_trip_sensor",
    "async_remove_trip_sensor",
    "async_remove_trip_emhass_sensor",
    "async_create_trip_emhass_sensor",
]
