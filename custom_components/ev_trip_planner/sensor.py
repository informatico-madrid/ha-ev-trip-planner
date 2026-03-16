"""Sensores para el componente EV Trip Planner.

Implementa entidades de sensores para mostrar información de viajes y carga.
Cumple con las reglas de Home Assistant 2026 para tipado estricto y runtime_data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CHARGING_POWER,
    CONF_CONSUMPTION,
    CONF_SAFETY_MARGIN,
    DEFAULT_CONSUMPTION,
    DEFAULT_SAFETY_MARGIN,
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)
from .trip_manager import TripManager

_LOGGER = logging.getLogger(__name__)

class TripPlannerSensor(SensorEntity):
    """Sensor base para el componente EV Trip Planner.

    Implementa la lógica común para todos los sensores del componente.
    Cumple con las reglas de Home Assistant 2026 para tipado estricto y runtime_data.
    """

    def __init__(self, hass: HomeAssistant, trip_manager: TripManager, sensor_type: str) -> None:
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

    async def async_update(self) -> None:
        """Actualiza el estado del sensor."""
        try:
            if self._sensor_type == "kwh_needed_today":
                self._attr_native_value = await self.trip_manager.async_get_kwh_needed_today()
            elif self._sensor_type == "hours_needed_today":
                self._attr_native_value = await self.trip_manager.async_get_hours_needed_today()
            elif self._sensor_type == "next_trip":
                next_trip = await self.trip_manager.async_get_next_trip()
                self._attr_native_value = next_trip["descripcion"] if next_trip else "N/A"
        except Exception as err:
            _LOGGER.error("Error actualizando sensor %s: %s", self._sensor_type, err)
            self._attr_native_value = None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Devuelve atributos adicionales para el sensor."""
        attrs = {}
        if self._sensor_type == "kwh_needed_today":
            attrs["viajes_hoy"] = len(await self.trip_manager.async_get_recurring_trips())
            attrs["viajes_puntuales"] = len(await self.trip_manager.async_get_punctual_trips())
        elif self._sensor_type == "hours_needed_today":
            attrs["potencia_carga"] = self.trip_manager.vehicle_controller.get_charging_power()
        elif self._sensor_type == "next_trip":
            next_trip = await self.trip_manager.async_get_next_trip()
            if next_trip:
                attrs["fecha_hora"] = next_trip["datetime"] if next_trip["tipo"] == TRIP_TYPE_PUNCTUAL else next_trip["dia_semana"]
                attrs["distancia"] = next_trip["km"]
                attrs["energia"] = next_trip["kwh"]
        return attrs

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
