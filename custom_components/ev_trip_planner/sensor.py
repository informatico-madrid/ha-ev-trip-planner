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
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import DATA_RUNTIME
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
        # Store cached attributes for synchronous access
        self._cached_attrs: Dict[str, Any] = {}

    async def async_update(self) -> None:
        """Actualiza el estado del sensor."""
        vehicle_id = getattr(self.trip_manager, "vehicle_id", "unknown")
        try:
            if self._sensor_type == "kwh_needed_today":
                _LOGGER.debug(  # noqa: E501
                    "Sensor update kwh_needed_today for %s: fetching trips data", vehicle_id
                )
                self._attr_native_value = await self.trip_manager.async_get_kwh_needed_today()
                # Cache attributes for synchronous access
                recurring = await self.trip_manager.async_get_recurring_trips()
                punctual = await self.trip_manager.async_get_punctual_trips()
                self._cached_attrs["viajes_hoy"] = len(recurring)
                self._cached_attrs["viajes_puntuales"] = len(punctual)
                _LOGGER.debug(  # noqa: E501
                    "Sensor update kwh_needed_today for %s: value=%s, recurring=%d, punctual=%d",
                    vehicle_id,
                    self._attr_native_value,
                    len(recurring),
                    len(punctual),
                )
            elif self._sensor_type == "hours_needed_today":
                _LOGGER.debug(  # noqa: E501
                    "Sensor update hours_needed_today for %s: fetching hours data", vehicle_id
                )
                self._attr_native_value = await self.trip_manager.async_get_hours_needed_today()
                charging_power = self.trip_manager.get_charging_power()
                self._cached_attrs["potencia_carga"] = charging_power
                _LOGGER.debug(  # noqa: E501
                    "Sensor update hours_needed_today for %s: value=%s, charging_power=%s",
                    vehicle_id,
                    self._attr_native_value,
                    charging_power,
                )
            elif self._sensor_type == "next_trip":
                _LOGGER.debug(  # noqa: E501
                    "Sensor update next_trip for %s: fetching next trip data", vehicle_id
                )
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
                    _LOGGER.debug(  # noqa: E501
                        "Sensor update next_trip for %s: next_trip=%s, datetime=%s, km=%s",
                        vehicle_id,
                        next_trip["descripcion"],
                        self._cached_attrs.get("fecha_hora"),
                        next_trip["km"],
                    )
                else:
                    self._cached_attrs.clear()
                    _LOGGER.debug(
                        "Sensor update next_trip for %s: no trips available", vehicle_id
                    )
        except Exception as err:
            _LOGGER.error(
                "Error actualizando sensor %s (vehicle=%s): %s",
                self._sensor_type,
                vehicle_id,
                err,
            )
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
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            _LOGGER.debug(
                "RecurringTripsCountSensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data and "recurring_trips" in data:
                return len(data.get("recurring_trips", []))
        _LOGGER.warning(
            "RecurringTripsCountSensor(%s) no coordinator data available", self._vehicle_id
        )
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
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            _LOGGER.debug(
                "PunctualTripsCountSensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data and "punctual_trips" in data:
                return len(data.get("punctual_trips", []))
        _LOGGER.warning(
            "PunctualTripsCountSensor(%s) no coordinator data available", self._vehicle_id
        )
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
            _LOGGER.debug(
                "TripsListSensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data:
                recurring = data.get("recurring_trips", [])
                punctual = data.get("punctual_trips", [])
                self._cached_attrs["recurring_trips"] = recurring
                self._cached_attrs["punctual_trips"] = punctual
                self._cached_attrs["trips"] = recurring + punctual
                return len(recurring) + len(punctual)
        _LOGGER.warning(
            "TripsListSensor(%s) no coordinator data available", self._vehicle_id
        )
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
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            _LOGGER.debug(
                "KwhTodaySensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data and "kwh_today" in data:
                return data.get("kwh_today", 0.0)
        _LOGGER.warning(
            "KwhTodaySensor(%s) no coordinator data available", self._vehicle_id
        )
        return 0.0


class HoursTodaySensor(TripPlannerSensor):
    """Sensor for hours needed today (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "hours_needed_today")
        self._attr_name = f"{vehicle_id} hours today"
        self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._vehicle_id = vehicle_id

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            _LOGGER.debug(
                "HoursTodaySensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data and "hours_today" in data:
                return data.get("hours_today", 0)
        _LOGGER.warning(
            "HoursTodaySensor(%s) no coordinator data available", self._vehicle_id
        )
        return 0


class NextTripSensor(TripPlannerSensor):
    """Sensor for next trip (alias for backward compatibility)."""

    def __init__(self, vehicle_id: str, coordinator: TripPlannerCoordinator) -> None:
        """Initialize sensor."""
        self._coordinator = coordinator
        trip_manager = getattr(coordinator, "trip_manager", coordinator)
        super().__init__(trip_manager.hass, trip_manager, "next_trip")
        self._attr_name = f"{vehicle_id} next trip"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._vehicle_id = vehicle_id

    @property
    def device_class(self) -> None:
        """Return device class (None for text sensor)."""
        return None

    @property
    def state_class(self) -> None:
        """Return state class (None for text sensor)."""
        return None

    @property
    def native_value(self) -> Any:
        """Return sensor value - read directly from coordinator.data."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "data"):
            data = self._coordinator.data
            _LOGGER.debug(
                "NextTripSensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data and "next_trip" in data:
                next_trip = data.get("next_trip")
                if next_trip:
                    return next_trip.get("descripcion", "No trips")
        _LOGGER.warning(
            "NextTripSensor(%s) no coordinator data available", self._vehicle_id
        )
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
            _LOGGER.debug(
                "NextDeadlineSensor(%s) reading from coordinator.data: %s",
                self._vehicle_id,
                data,
            )
            if data and "next_trip" in data:
                next_trip = data.get("next_trip")
                if next_trip:
                    return next_trip.get("datetime")
        _LOGGER.warning(
            "NextDeadlineSensor(%s) no coordinator data available", self._vehicle_id
        )
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
            _LOGGER.debug(
                "EmhassDeferrableLoadSensor update for %s: charging_power=%s, horizon=%s",
                self._vehicle_id,
                charging_power_kw,
                planning_horizon_days,
            )

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
            _LOGGER.debug(
                "EmhassDeferrableLoadSensor update for %s: ready, profile_len=%d, schedule_len=%d",
                self._vehicle_id,
                len(power_profile) if power_profile else 0,
                len(schedule) if schedule else 0,
            )

        except Exception as err:
            _LOGGER.error(
                "Error actualizando sensor EMHASS %s: %s",
                self._vehicle_id,
                err,
                exc_info=True,
            )
            self._attr_native_value = "error"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Any
) -> bool:
    """Set up sensors from config entry."""
    vehicle_id = entry.data.get("vehicle_name", "")
    entry_id = entry.entry_id
    namespace = f"ev_trip_planner_{entry_id}"

    # Use DATA_RUNTIME namespace correctly
    runtime_data = hass.data.get(DATA_RUNTIME, {})
    namespace_data = runtime_data.get(namespace, {})
    trip_manager = namespace_data.get("trip_manager")
    coordinator = namespace_data.get("coordinator")

    _LOGGER.debug(
        "trip_manager lookup for %s: namespace=%s, found=%s",
        vehicle_id,
        namespace,
        trip_manager is not None,
    )

    if not trip_manager:
        # Legacy fallback for older configurations
        _LOGGER.debug(
            "trip_manager lookup: trying legacy fallback for %s (entry_id=%s)",
            vehicle_id,
            entry_id,
        )
        trip_manager = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("trip_manager")
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("coordinator")
        _LOGGER.debug(
            "trip_manager lookup: legacy fallback result for %s: found=%s",
            vehicle_id,
            trip_manager is not None,
        )

    if not trip_manager:
        _LOGGER.error(
            "No trip_manager found for %s (namespace=%s, runtime_data keys=%s)",
            vehicle_id,
            namespace,
            list(runtime_data.keys()) if runtime_data else [],
            exc_info=True,
        )
        return False

    _LOGGER.debug(
        "Setting up sensors for vehicle_id=%s, entry_id=%s, coordinator=%s",
        vehicle_id,
        entry_id,
        coordinator is not None,
    )

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

    _LOGGER.debug(
        "Created sensors for %s: %s",
        vehicle_id,
        [type(e).__name__ for e in entities],
    )

    async_add_entities(entities)
    return True
