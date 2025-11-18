"""Sensores informacionales para EV Trip Planner (Fase 1C) con Coordinator."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, SIGNAL_TRIPS_UPDATED, TRIP_TYPE_PUNCTUAL, TRIP_TYPE_RECURRING
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)
class TripsCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, vehicle_id: str, trip_manager: TripManager) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"EV Trip Planner {vehicle_id}",
        )
        self._mgr = trip_manager
        self._vehicle_id = vehicle_id

    async def _async_update_data(self) -> list[dict[str, Any]]:
        return await self._mgr.async_get_all_trips()


class _BaseTripSensor(CoordinatorEntity[TripsCoordinator], SensorEntity):
    _attr_should_poll = False

    def __init__(self, vehicle_id: str, coordinator: TripsCoordinator) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_extra_state_attributes = {}


class RecurringTripsCountSensor(_BaseTripSensor):
    def __init__(self, vehicle_id: str, coordinator: TripsCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} recurring trips count"
        self._attr_unique_id = f"{vehicle_id}_recurring_trips_count"

    @property
    def native_value(self) -> int:
        trips = self.coordinator.data or []
        return len([t for t in trips if t.get("tipo") == TRIP_TYPE_RECURRING])


class PunctualTripsCountSensor(_BaseTripSensor):
    def __init__(self, vehicle_id: str, coordinator: TripsCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} punctual trips count"
        self._attr_unique_id = f"{vehicle_id}_punctual_trips_count"

    @property
    def native_value(self) -> int:
        trips = self.coordinator.data or []
        return len([t for t in trips if t.get("tipo") == TRIP_TYPE_PUNCTUAL])


class TripsListSensor(_BaseTripSensor):
    def __init__(self, vehicle_id: str, coordinator: TripsCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} trips list"
        self._attr_unique_id = f"{vehicle_id}_trips_list"

    @property
    def native_value(self) -> int:
        # Valor nativo: total de viajes
        trips = self.coordinator.data or []
        return len(trips)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return {"trips": self.coordinator.data or []}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry.
    
    Creates three informational sensors:
    - trips_list: total trips with details in attributes
    - recurring_trips_count: count of recurring trips
    - punctual_trips_count: count of punctual trips
    """
    vehicle_id = entry.data.get("vehicle_name", "EV")
    entry_id = entry.entry_id
    
    # Get shared TripManager instance
    trip_manager = hass.data[DOMAIN][entry_id]["trip_manager"]

    # Create coordinator
    coordinator = TripsCoordinator(hass, vehicle_id, trip_manager)

    # Initial refresh
    coordinator.async_set_updated_data(await trip_manager.async_get_all_trips())

    # Subscribe to dispatcher for reactive updates: push new data into coordinator
    signal = f"{SIGNAL_TRIPS_UPDATED}_{vehicle_id}"

    async def _handle_trips_updated() -> None:
        new_trips = await trip_manager.async_get_all_trips()
        coordinator.async_set_updated_data(new_trips)

    async_dispatcher_connect(hass, signal, _handle_trips_updated)

    # Create sensor instances with shared TripManager
    trips_list = TripsListSensor(vehicle_id, coordinator)
    recurring_count = RecurringTripsCountSensor(vehicle_id, coordinator)
    punctual_count = PunctualTripsCountSensor(vehicle_id, coordinator)

    # Override unique_id with entry_id-based pattern for HA entity registry
    trips_list._attr_unique_id = f"{entry_id}_trips_list"
    recurring_count._attr_unique_id = f"{entry_id}_recurring_trips_count"
    punctual_count._attr_unique_id = f"{entry_id}_punctual_trips_count"

    async_add_entities([trips_list, recurring_count, punctual_count])
