from custom_components.ev_trip_planner.trip._sensor_callbacks import SensorCallbackRegistry
from custom_components.ev_trip_planner.trip._types import CargaVentana
from custom_components.ev_trip_planner.trip._types import SOCMilestoneResult

__all__ = ["TripManager", "CargaVentana", "SOCMilestoneResult", "SensorCallbackRegistry"]


def __getattr__(name):
    """Lazy import to avoid circular dependency with trip_manager."""
    if name == "TripManager":
        from custom_components.ev_trip_planner.trip_manager import TripManager

        return TripManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
