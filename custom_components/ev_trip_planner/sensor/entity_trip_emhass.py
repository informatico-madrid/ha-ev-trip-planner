"""TripEmhassSensor entity implementation.

Extracted from sensor_orig.py as part of the SOLID decomposition (Spec 3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import TripPlannerCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo

# 9 documented attributes for TripEmhassSensor
# Prevents data leak of internal cache keys (activo, *_array, p_deferrable_matrix, etc.)
TRIP_EMHASS_ATTR_KEYS = {
    "def_total_hours",
    "P_deferrable_nom",
    "def_start_timestep",
    "def_end_timestep",
    "power_profile_watts",
    "trip_id",
    "emhass_index",
    "kwh_needed",
    "deadline",
}

# Re-export for backwards compatibility
__all__ = ["TripEmhassSensor", "TRIP_EMHASS_ATTR_KEYS"]


class TripEmhassSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity,  # type: ignore[misc]  # HA stub: CoordinatorEntity mixin typing
):
    """Sensor for per-trip EMHASS parameters.

    This is a new sensor class for PHASE 4, separate from existing trip sensors.
    It reads emhass_index from coordinator.data["per_trip_emhass_params"].

    Attributes:
        native_value: The emhass_index for the trip, or -1 if not found
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        trip_id: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            trip_id: Trip identifier.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self._trip_id = trip_id
        self._attr_unique_id = f"emhass_trip_{vehicle_id}_{trip_id}"
        self._attr_has_entity_name = True
        self._attr_name = f"EMHASS Index for {trip_id}"

    @property
    def native_value(self) -> int:
        """Return the emhass_index for this trip.

        Reads from coordinator.data["per_trip_emhass_params"][trip_id]["emhass_index"].
        Returns -1 if trip not found or emhass_index not available.

        Returns:
            The emhass_index integer, or -1 if not found.
        """
        if self.coordinator.data is None:
            return -1

        per_trip_params = self.coordinator.data.get("per_trip_emhass_params", {})
        trip_params = per_trip_params.get(self._trip_id, {})
        emhass_index = trip_params.get("emhass_index", -1)

        return emhass_index if emhass_index is not None else -1

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes for this trip.

        Returns all 9 per-trip EMHASS parameters:
        - def_total_hours, P_deferrable_nom, def_start_timestep, def_end_timestep
        - power_profile_watts, trip_id, emhass_index, kwh_needed, deadline

        Returns:
            Dict with all 9 keys, or zeroed values if trip not found.
        """
        if self.coordinator.data is None:
            return self._zeroed_attributes()

        per_trip_params = self.coordinator.data.get("per_trip_emhass_params", {})
        trip_params = per_trip_params.get(self._trip_id)

        if trip_params is None:
            return self._zeroed_attributes()

        # Filter to ONLY the 9 documented keys — prevents data leak
        return {k: v for k, v in trip_params.items() if k in TRIP_EMHASS_ATTR_KEYS}

    def _zeroed_attributes(self) -> Dict[str, Any]:
        """Return zeroed/default values for all 9 attributes.

        Used when trip not found or data unavailable.

        Returns:
            Dict with all 9 keys set to zero/None/empty values.
        """
        return {
            "def_total_hours": 0.0,
            "P_deferrable_nom": 0.0,
            "def_start_timestep": 0,
            "def_end_timestep": 24,
            "power_profile_watts": [],
            "trip_id": self._trip_id,
            "emhass_index": -1,
            "kwh_needed": 0.0,
            "deadline": None,
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for this sensor.

        Uses device identifiers={(DOMAIN, vehicle_id)} to group
        all TripEmhassSensor instances under the same vehicle device.

        Returns:
            DeviceInfo with 'identifiers' key containing {(DOMAIN, vehicle_id)},
            or None if not configured.
        """
        return dr.DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
        )
