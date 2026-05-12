"""TripSensor entity implementation.

Extracted from sensor_orig.py as part of the SOLID decomposition (Spec 3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import EntityCategory  # type: ignore[attr-defined]  # HA stub: EntityCategory not explicitly exported
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN, TRIP_TYPE_PUNCTUAL
from ..coordinator import TripPlannerCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo


class TripSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity,  # type: ignore[misc]  # HA stub: CoordinatorEntity mixin typing
):
    """Sensor for a specific trip using CoordinatorEntity pattern.

    Reads trip data from coordinator.data["recurring_trips"][trip_id] or
    coordinator.data["punctual_trips"][trip_id].

    Entity: sensor.ev_trip_planner_{vehicle_id}_trip_{trip_id}
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        trip_id: str,
    ) -> None:
        """Initialize the trip sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            trip_id: Trip identifier.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self._trip_id = trip_id
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_trip_{trip_id}"
        self._attr_name = f"Trip {trip_id}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_state_class = None
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Set enum options for estado
        self._attr_options = [
            "active",
            "pendiente",
            "completado",
            "cancelado",
            "recurrente",
        ]

    def _get_trip_data(self) -> Dict[str, Any]:
        """Get trip data from coordinator.

        Returns:
            Trip data dict or empty dict if not found.
        """
        if self.coordinator.data is None:
            return {}
        recurring_trips = self.coordinator.data.get("recurring_trips", {})
        punctual_trips = self.coordinator.data.get("punctual_trips", {})
        trip_data = recurring_trips.get(self._trip_id)
        if trip_data is None:
            trip_data = punctual_trips.get(self._trip_id)
        return trip_data if trip_data is not None else {}

    @property
    def native_value(self) -> Any:
        """Return sensor value (trip estado)."""
        trip_data = self._get_trip_data()
        if not trip_data:
            return None
        trip_type = trip_data.get("tipo", "unknown")
        if trip_type == TRIP_TYPE_PUNCTUAL:
            return trip_data.get("estado", "pendiente")
        return "recurrente"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return trip details as attributes."""
        trip_data = self._get_trip_data()
        if not trip_data:
            return {}
        return {
            "trip_id": trip_data.get("id", self._trip_id),
            "trip_type": trip_data.get("tipo", "unknown"),
            "descripcion": trip_data.get("descripcion", ""),
            "km": trip_data.get("km", 0.0),
            "kwh": trip_data.get("kwh", 0.0),
            "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
            "activo": trip_data.get("activo", True),
            "estado": trip_data.get("estado", "pendiente"),
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for the trip sensor."""
        return dr.DeviceInfo(
            identifiers={(DOMAIN, f"{self._vehicle_id}_{self._trip_id}")},
            name=f"Trip {self._trip_id} - {self._vehicle_id}",
            manufacturer="Home Assistant",
            model="EV Trip Planner",
            sw_version="2026.3.0",
            via_device=(DOMAIN, self._vehicle_id),
        )
