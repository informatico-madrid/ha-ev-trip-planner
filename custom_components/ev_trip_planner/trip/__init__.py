from custom_components.ev_trip_planner.trip._sensor_callbacks import (
    SensorCallbackRegistry,
)
from custom_components.ev_trip_planner.trip._trip_navigator import DAYS_OF_WEEK
from custom_components.ev_trip_planner.trip._types import (
    CargaVentana,
    SOCMilestoneResult,
    TripManagerConfig,
)
from custom_components.ev_trip_planner.trip.manager import TripManager
from custom_components.ev_trip_planner.trip.state import TripManagerState

# Re-export constants that tests imported from old trip_manager
from ..const import DEFAULT_CHARGING_POWER  # noqa: F401 — test compatibility

__all__ = [
    "TripManager",
    "TripManagerConfig",
    "TripManagerState",
    "DEFAULT_CHARGING_POWER",
    "CargaVentana",
    "SOCMilestoneResult",
    "SensorCallbackRegistry",
    "DAYS_OF_WEEK",
]
