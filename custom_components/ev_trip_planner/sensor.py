"""Sensores informacionales para EV Trip Planner (Fase 1C) con TripPlannerCoordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TripPlannerCoordinator
from .const import DOMAIN, TRIP_TYPE_PUNCTUAL, TRIP_TYPE_RECURRING

_LOGGER = logging.getLogger(__name__)


class _BaseTripSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    _attr_should_poll = False

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_extra_state_attributes = {}


class RecurringTripsCountSensor(_BaseTripSensor):
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} recurring trips count"
        self._attr_unique_id = f"{vehicle_id}_recurring_trips_count"

    @property
    def native_value(self) -> int:
        data = self.coordinator.data or {}
        trips = data.get("recurring_trips", [])
        return len(trips)


class PunctualTripsCountSensor(_BaseTripSensor):
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} punctual trips count"
        self._attr_unique_id = f"{vehicle_id}_punctual_trips_count"

    @property
    def native_value(self) -> int:
        data = self.coordinator.data or {}
        trips = data.get("punctual_trips", [])
        return len(trips)


class TripsListSensor(_BaseTripSensor):
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} trips list"
        self._attr_unique_id = f"{vehicle_id}_trips_list"

    @property
    def native_value(self) -> int:
        # Valor nativo: total de viajes
        data = self.coordinator.data or {}
        recurring = data.get("recurring_trips", [])
        punctual = data.get("punctual_trips", [])
        return len(recurring) + len(punctual)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        recurring = data.get("recurring_trips", [])
        punctual = data.get("punctual_trips", [])
        return {
            "trips": recurring + punctual,  # Combined for dashboard compatibility
            "recurring_trips": recurring,   # Backward compatibility
            "punctual_trips": punctual      # Backward compatibility
        }


class NextTripSensor(_BaseTripSensor):
    """Sensor que muestra la descripción del próximo viaje."""
    
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} next trip"
        self._attr_unique_id = f"{vehicle_id}_next_trip"
    
    @property
    def native_value(self) -> str:
        """Devuelve la descripción del próximo viaje directamente desde coordinator.data."""
        try:
            next_trip = self.coordinator.data.get("next_trip")
            if next_trip:
                return next_trip.get("descripcion", "Viaje")
            return "No trips"
        except Exception as err:
            _LOGGER.error("Error getting next trip from coordinator: %s", err)
            return "Error"


class NextDeadlineSensor(_BaseTripSensor):
    """Sensor que muestra la fecha/hora del próximo viaje."""
    
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} next deadline"
        self._attr_unique_id = f"{vehicle_id}_next_deadline"
        self._attr_device_class = "timestamp"
    
    @property
    def native_value(self) -> datetime | None:
        """Devuelve el datetime del próximo viaje directamente desde coordinator.data."""
        try:
            next_trip = self.coordinator.data.get("next_trip")
            if next_trip:
                return next_trip.get("datetime")
            return None
        except Exception as err:
            _LOGGER.error("Error getting next deadline from coordinator: %s", err)
            return None


class KwhTodaySensor(_BaseTripSensor):
    """Sensor que muestra la suma de kWh necesarios hoy."""
    
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} kwh today"
        self._attr_unique_id = f"{vehicle_id}_kwh_today"
        self._attr_unit_of_measurement = "kWh"
    
    @property
    def native_value(self) -> float:
        """Devuelve la suma de kWh para hoy directamente desde coordinator.data."""
        try:
            return self.coordinator.data.get("kwh_today", 0.0)
        except Exception as err:
            _LOGGER.error("Error getting kWh today from coordinator: %s", err)
            return 0.0


class HoursTodaySensor(_BaseTripSensor):
    """Sensor que muestra las horas de carga necesarias (redondeo hacia arriba)."""
    
    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        super().__init__(vehicle_id, coordinator)
        self._attr_name = f"{vehicle_id} hours today"
        self._attr_unique_id = f"{vehicle_id}_hours_today"
        self._attr_unit_of_measurement = "h"
    
    @property
    def native_value(self) -> int:
        """Devuelve las horas de carga necesarias directamente desde coordinator.data."""
        try:
            return self.coordinator.data.get("hours_today", 0)
        except Exception as err:
            _LOGGER.error("Error getting hours today from coordinator: %s", err)
            return 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry.
    
    Creates seven informational sensors:
    - trips_list: total trips with details in attributes
    - recurring_trips_count: count of recurring trips
    - punctual_trips_count: count of punctual trips
    - next_trip: description of next upcoming trip
    - next_deadline: datetime of next upcoming trip
    - kwh_today: sum of kWh needed for today's trips
    - hours_today: hours needed to charge (rounded up)
    """
    vehicle_id = entry.data.get("vehicle_name", "EV")
    entry_id = entry.entry_id
    
    # FIX: Usar el coordinator ya creado en async_setup_entry, no crear uno nuevo
    coordinator = hass.data[DOMAIN][entry_id]["coordinator"]
    
    # FIX: No hacer refresh aquí, ya se hizo en async_setup_entry
    # await coordinator.async_config_entry_first_refresh()

    # Create sensor instances with shared TripManager
    trips_list = TripsListSensor(vehicle_id, coordinator)
    recurring_count = RecurringTripsCountSensor(vehicle_id, coordinator)
    punctual_count = PunctualTripsCountSensor(vehicle_id, coordinator)
    next_trip = NextTripSensor(vehicle_id, coordinator)
    next_deadline = NextDeadlineSensor(vehicle_id, coordinator)
    kwh_today = KwhTodaySensor(vehicle_id, coordinator)
    hours_today = HoursTodaySensor(vehicle_id, coordinator)

    # Override unique_id with entry_id-based pattern for HA entity registry
    trips_list._attr_unique_id = f"{entry_id}_trips_list"
    recurring_count._attr_unique_id = f"{entry_id}_recurring_trips_count"
    punctual_count._attr_unique_id = f"{entry_id}_punctual_trips_count"
    next_trip._attr_unique_id = f"{entry_id}_next_trip"
    next_deadline._attr_unique_id = f"{entry_id}_next_deadline"
    kwh_today._attr_unique_id = f"{entry_id}_kwh_today"
    hours_today._attr_unique_id = f"{entry_id}_hours_today"

    async_add_entities([
        trips_list, recurring_count, punctual_count,
        next_trip, next_deadline, kwh_today, hours_today
    ])
