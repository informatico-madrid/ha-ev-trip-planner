"""Sensor package for EV Trip Planner.

Re-exports all public names from the decomposed sensor/ package.

The legacy sensor.py module was replaced by a sensor/ package directory.
This __init__.py re-exports every public name so that existing import
paths continue to work without changes.
"""

from __future__ import annotations

# Platform entry point and helpers from _async_setup.
from ._async_setup import (
    TRIP_SENSORS,
    _async_create_trip_sensors,  # noqa: F401  # Used internally by HA entity platform
    async_create_trip_emhass_sensor,
    async_create_trip_sensor,
    async_remove_trip_emhass_sensor,
    async_remove_trip_sensor,
    async_setup_entry,
    async_update_trip_sensor,
)

# Entity classes from sub-modules.
from .entity_emhass_deferrable import EmhassDeferrableLoadSensor
from .entity_trip import TripSensor
from .entity_trip_emhass import TRIP_EMHASS_ATTR_KEYS, TripEmhassSensor
from .entity_trip_planner import TripPlannerSensor

__all__ = [
    "TRIP_SENSORS",
    "TRIP_EMHASS_ATTR_KEYS",
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
