"""TripPlannerSensor entity implementation.

Extracted from sensor_orig.py as part of the SOLID decomposition (Spec 3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from homeassistant.components.sensor import RestoreSensor, SensorEntity  # noqa: F401
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import (
    EntityCategory,  # type: ignore[attr-defined]  # HA stub: EntityCategory not explicitly exported
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import TripPlannerCoordinator
from ..definitions import TripSensorEntityDescription

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo


class TripPlannerSensor(
    CoordinatorEntity[TripPlannerCoordinator],  # type: ignore[misc]  # HA stub: CoordinatorEntity mixin typing
    RestoreSensor,
    SensorEntity,
):
    """Sensor base for EV Trip Planner using CoordinatorEntity pattern.

    Reads from coordinator.data via entity_description.value_fn().
    Sets _attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}".
    Inherits RestoreSensor for state restoration on HA restart.
    """

    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        entity_description: TripSensorEntityDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: TripPlannerCoordinator instance.
            vehicle_id: Vehicle identifier.
            entity_description: Description with value_fn and attrs_fn.
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._vehicle_id = vehicle_id
        self.entity_description = entity_description
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{entity_description.key}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_name = f"EV Trip Planner {entity_description.key}"
        # Store cached attributes for synchronous access
        self._cached_attrs: Dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass.

        Restores state if restore=True and coordinator.data is None.
        """
        await super().async_added_to_hass()
        restore_val = getattr(self.entity_description, "restore", False)
        if restore_val and self.coordinator.data is None:
            # Restore state from previous run
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._attr_native_value = last_state.state

    @property
    def native_value(self) -> Any:
        """Return sensor value via entity_description.value_fn."""
        if self.coordinator.data is None:
            return None
        value_fn = getattr(self.entity_description, "value_fn", lambda _: None)
        return value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return attributes from coordinator.data via entity_description.attrs_fn."""
        if self.coordinator.data is None:
            return {}
        attrs_fn: Callable[[Dict[str, Any]], Dict[str, Any]] = getattr(
            self.entity_description, "attrs_fn", lambda _: {}
        )
        return attrs_fn(self.coordinator.data)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device info for the vehicle."""
        return dr.DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
            name=f"EV Trip Planner {self._vehicle_id}",
            manufacturer="Home Assistant",
            model="EV Trip Planner",
            sw_version="2026.3.0",
        )
