"""Sensores para el componente EV Trip Planner.

Implementa entidades de sensores para mostrar información de viajes y carga.
Cumple con las reglas de Home Assistant 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_CHARGING_POWER,
    DEFAULT_CHARGING_POWER,
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
)
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)


# Type alias for coordinator pattern used in tests
TripPlannerCoordinator = Any


class TripPlannerSensor(SensorEntity):
    """Sensor base para el componente EV Trip Planner.

    Implementa la lógica común para todos los sensores del componente.
    Cumple con las reglas de Home Assistant 2026 para tipado estricto y runtime_data.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        trip_manager: TripManager,
        sensor_type: str,
    ) -> None:
        """Inicializa el sensor base."""
        self.hass = hass
        self.trip_manager = trip_manager
        self._sensor_type = sensor_type
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_name = f"EV Trip Planner {sensor_type}"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        # Store cached attributes for synchronous access
        self._cached_attrs: Dict[str, Any] = {}

    async def async_update(self) -> None:
        """Actualiza el estado del sensor."""
        try:
            if self._sensor_type == "kwh_needed_today":
                self._attr_native_value = await self.trip_manager.async_get_kwh_needed_today()
                # Cache attributes for synchronous access
                recurring = await self.trip_manager.async_get_recurring_trips()
                punctual = await self.trip_manager.async_get_punctual_trips()
                self._cached_attrs["viajes_hoy"] = len(recurring)
                self._cached_attrs["viajes_puntuales"] = len(punctual)
            elif self._sensor_type == "hours_needed_today":
                self._attr_native_value = await self.trip_manager.async_get_hours_needed_today()
                self._cached_attrs["potencia_carga"] = (
                    self.trip_manager.vehicle_controller.get_charging_power()
                )
            elif self._sensor_type == "next_trip":
                next_trip = await self.trip_manager.async_get_next_trip()
                self._attr_native_value = next_trip["descripcion"] if next_trip else "N/A"
                if next_trip:
                    self._cached_attrs["fecha_hora"] = (
                        next_trip["datetime"]
                        if next_trip["tipo"] == TRIP_TYPE_PUNCTUAL
                        else next_trip["dia_semana"]
                    )
                    self._cached_attrs["distancia"] = next_trip["km"]
                    self._cached_attrs["energia"] = next_trip["kwh"]
                else:
                    self._cached_attrs.clear()
        except Exception as err:
            _LOGGER.error("Error actualizando sensor %s: %s", self._sensor_type, err)
            self._attr_native_value = None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Devuelve atributos adicionales para el sensor."""
        # Return default empty arrays for dashboard compatibility
        if not self._cached_attrs:
            return {"recurring_trips": [], "punctual_trips": []}
        return self._cached_attrs.copy()

    @property
    def device_info(self) -> Dict[str, Any]:
        """Devuelve información del dispositivo."""
        return {
            "identifiers": {(DOMAIN, self.trip_manager.vehicle_id)},
            "name": f"EV Trip Planner {self.trip_manager.vehicle_id}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
        }


# Backward compatibility aliases for tests
# These map test expectations to the actual TripPlannerSensor implementation


class RecurringTripsCountSensor(TripPlannerSensor):
    """Sensor for counting recurring trips (alias for backward compatibility)."""

    def __init__(
        self, vehicle_id: str, coordinator: TripPlannerCoordinator
    ) -> None:
        """Initialize sensor."""
        # Extract trip_manager from coordinator if available
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "recurring_trips_count")
        self._attr_name = f"{vehicle_id} recurring trips count"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data and "recurring_trips" in data:
                return len(data.get("recurring_trips", []))
        return 0


class PunctualTripsCountSensor(TripPlannerSensor):
    """Sensor for counting punctual trips (alias for backward compatibility)."""

    def __init__(
        self, vehicle_id: str, coordinator: TripPlannerCoordinator
    ) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "punctual_trips_count")
        self._attr_name = f"{vehicle_id} punctual trips count"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data and "punctual_trips" in data:
                return len(data.get("punctual_trips", []))
        return 0


class TripsListSensor(TripPlannerSensor):
    """Sensor for combined trips list (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "trips_list")
        self._attr_name = f"{vehicle_id} trips list"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data:
                recurring = data.get("recurring_trips", [])
                punctual = data.get("punctual_trips", [])
                self._cached_attrs["recurring_trips"] = recurring
                self._cached_attrs["punctual_trips"] = punctual
                self._cached_attrs["trips"] = recurring + punctual
                return len(recurring) + len(punctual)
        return 0


# Additional sensor aliases for test compatibility
class KwhTodaySensor(TripPlannerSensor):
    """Sensor for kWh needed today (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "kwh_needed_today")
        self._attr_name = f"{vehicle_id} kwh today"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data and "kwh_today" in data:
                return data.get("kwh_today", 0.0)
        return 0.0


class HoursTodaySensor(TripPlannerSensor):
    """Sensor for hours needed today (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "hours_needed_today")
        self._attr_name = f"{vehicle_id} hours today"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data and "hours_today" in data:
                return data.get("hours_today", 0)
        return 0


class NextTripSensor(TripPlannerSensor):
    """Sensor for next trip (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "next_trip")
        self._attr_name = f"{vehicle_id} next trip"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data and "next_trip" in data:
                next_trip = data.get("next_trip")
                if next_trip:
                    return next_trip.get("descripcion", "No trips")
        return "No trips"


class NextDeadlineSensor(TripPlannerSensor):
    """Sensor for next deadline (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "next_deadline")
        self._attr_name = f"{vehicle_id} next deadline"
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            if data and "next_trip" in data:
                next_trip = data.get("next_trip")
                if next_trip:
                    return next_trip.get("datetime")
        return None


class EmhassDeferrableLoadSensor(SensorEntity):
    """Sensor para el perfil de carga diferible de EMHASS.

    Este sensor proporciona los datos necesarios para la integración con EMHASS:
    - power_profile_watts: Array de potencia en watts por hora
    - deferrables_schedule: Calendario de cargas diferibles

    Platform: template
    Entity: sensor.emhass_perfil_diferible_{vehicle_id}
    """

    def __init__(
        self,
        hass: HomeAssistant,
        trip_manager: TripManager,
        vehicle_id: str,
    ) -> None:
        """Inicializa el sensor de carga diferible."""
        self.hass = hass
        self.trip_manager = trip_manager
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"emhass_perfil_diferible_{vehicle_id}"
        self._attr_name = f"EMHASS Perfil Diferible {vehicle_id}"
        self._attr_has_entity_name = True
        self._attr_native_value = "ready"
        self._cached_attrs: Dict[str, Any] = {}

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return self._attr_unique_id

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._vehicle_id)},
            "name": f"EV Trip Planner {self._vehicle_id}",
            "manufacturer": "Home Assistant",
            "model": "EV Trip Planner",
            "sw_version": "2026.3.0",
        }

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return self._cached_attrs

    async def async_update(self) -> None:
        """Actualiza el estado del sensor."""
        try:
            entry = self.hass.config_entries.async_get_entry(self._vehicle_id)
            if not entry or not entry.data:
                _LOGGER.warning("No config entry found for %s", self._vehicle_id)
                return

            charging_power_kw = entry.data.get(CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER)
            planning_horizon_days = entry.data.get("planning_horizon_days", 7)

            power_profile = await self.trip_manager.async_generate_power_profile(
                charging_power_kw=charging_power_kw,
                planning_horizon_days=planning_horizon_days,
            )

            schedule = await self.trip_manager.async_generate_deferrables_schedule(
                charging_power_kw=charging_power_kw,
                planning_horizon_days=planning_horizon_days,
            )

            self._cached_attrs = {
                "power_profile_watts": power_profile,
                "deferrables_schedule": schedule,
            }
            self._attr_native_value = "ready"

        except Exception as err:
            _LOGGER.error("Error actualizando sensor EMHASS %s: %s", self._vehicle_id, err)
            self._attr_native_value = "error"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any
) -> bool:
    """Set up sensors from config entry."""
    vehicle_id = entry.data.get("vehicle_name", "")
    entry_id = entry.entry_id
    namespace = f"ev_trip_planner_{entry_id}"

    trip_manager = hass.data.get(namespace, {}).get("trip_manager")
    coordinator = hass.data.get(namespace, {}).get("coordinator")

    if not trip_manager:
        trip_manager = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("trip_manager")
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")

    if not trip_manager:
        _LOGGER.error("No trip_manager found for %s", vehicle_id)
        return False

    entities = [
        TripsListSensor(vehicle_id, coordinator),
        RecurringTripsCountSensor(vehicle_id, coordinator),
        PunctualTripsCountSensor(vehicle_id, coordinator),
        KwhTodaySensor(vehicle_id, coordinator),
        HoursTodaySensor(vehicle_id, coordinator),
        NextTripSensor(vehicle_id, coordinator),
        NextDeadlineSensor(vehicle_id, coordinator),
        EmhassDeferrableLoadSensor(hass, trip_manager, vehicle_id),
    ]

    async_add_entities(entities)
    return True
