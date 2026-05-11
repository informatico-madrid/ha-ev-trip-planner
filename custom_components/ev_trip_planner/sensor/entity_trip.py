"""TripSensor entity — transitional re-export.

Re-exports the class from the legacy sensor_orig.py module.
Once decomposition is complete, this file will contain the
actual implementation.
"""

from __future__ import annotations

from custom_components.ev_trip_planner.sensor_orig import TripSensor

__all__ = ["TripSensor"]
