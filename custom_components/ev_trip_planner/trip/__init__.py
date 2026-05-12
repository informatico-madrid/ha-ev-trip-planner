from custom_components.ev_trip_planner.trip._crud_mixin import _CRUDMixin
from custom_components.ev_trip_planner.trip._power_profile_mixin import _PowerProfileMixin
from custom_components.ev_trip_planner.trip._schedule_mixin import _ScheduleMixin
from custom_components.ev_trip_planner.trip._sensor_callbacks import SensorCallbackRegistry
from custom_components.ev_trip_planner.trip._soc_mixin import _SOCMixin
from custom_components.ev_trip_planner.trip._types import CargaVentana
from custom_components.ev_trip_planner.trip._types import SOCMilestoneResult
from custom_components.ev_trip_planner.trip.manager import TripManager
from custom_components.ev_trip_planner.trip.state import TripManagerState

# Re-export constants that tests imported from old trip_manager
from ..const import DEFAULT_CHARGING_POWER  # noqa: F401 — test compatibility

__all__ = [
    "TripManager",
    "TripManagerState",
    "DEFAULT_CHARGING_POWER",
    "CargaVentana",
    "SOCMilestoneResult",
    "SensorCallbackRegistry",
    "_CRUDMixin",
    "_SOCMixin",
    "_PowerProfileMixin",
    "_ScheduleMixin",
]
