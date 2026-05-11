"""Transitional shim — re-export everything from the sensor/ package.

The legacy sensor.py module file has been replaced by a sensor/ package
directory as part of the SOLID decomposition (Spec 3). This shim ensures
that existing import paths (from .sensor import ...) continue to work
during the transitional phase.

Once all consumers migrate to the package path, this file can be removed.
"""

from __future__ import annotations

# Re-export all public names from the sensor/ package.
# These come from sensor/__init__.py which imports from sensor_orig.py.
from custom_components.ev_trip_planner.sensor import (  # noqa: F401
    EmhassDeferrableLoadSensor,
    TripEmhassSensor,
    TripPlannerSensor,
    TripSensor,
    async_create_trip_emhass_sensor,
    async_create_trip_sensor,
    async_remove_trip_emhass_sensor,
    async_remove_trip_sensor,
    async_setup_entry,
    async_update_trip_sensor,
)
