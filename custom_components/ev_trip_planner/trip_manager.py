"""Backward-compat re-export for trip_manager.

The TripManager class has been moved to the trip/ package.
This file re-exports it for existing imports.
"""

import yaml  # noqa: F401 — re-export for test backward compatibility

from custom_components.ev_trip_planner.trip.manager import _UNSET  # noqa: F401 — re-export
from custom_components.ev_trip_planner.trip.manager import TripManager

__all__ = ["TripManager", "_UNSET"]
