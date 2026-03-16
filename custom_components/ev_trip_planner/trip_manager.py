"""Gestión central de viajes y optimización de carga para vehículos eléctricos.

Implementa la lógica de planificación de viajes, cálculo de energía necesaria
y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
runtime_data y tipado estricto.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

import voluptuous as vol
from homeassistant.components import recorder
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
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
from .vehicle_controller import VehicleController

_LOGGER = logging.getLogger(__name__)

class TripManager:
    """Gestión central de viajes y optimización de carga para vehículos eléctricos.

    Esta clase implementa la lógica de planificación de viajes, cálculo de energía necesaria
    y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
    runtime_data y tipado estricto.
    """

    def __init__(self, hass: HomeAssistant, vehicle_id: str) -> None:
        """Inicializa el gestor de viajes para un vehículo específico."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self.vehicle_controller = VehicleController(hass, vehicle_id)
        self._trips: Dict[str, Any] = {}
        self._recurring_trips: Dict[str, Any] = {}
        self._punctual_trips: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None

    async def async_setup(self) -> None:
        """Configura el gestor de viajes y carga los datos desde el almacenamiento."""
        _LOGGER.info("Configurando gestor de viajes para vehículo: %s", self.vehicle_id)
        await self.vehicle_controller.async_setup()
        await self._load_trips()

    async def _load_trips(self) -> None:
        """Carga los viajes desde el almacenamiento persistente."""
        try:
            # FIX: Usar namespace con entry_id para acceso seguro a runtime_data
            namespace = f"{DOMAIN}_{self.hass.config_entries.async_get_entry(self.vehicle_id).entry_id}"
            self._trips = self.hass.data.get(namespace, {}).get("trips", {})
            self._recurring_trips = self.hass.data.get(namespace, {}).get("recurring_trips", {})
            self._punctual_trips = self.hass.data.get(namespace, {}).get("punctual_trips", {})
            self._last_update = self.hass.data.get(namespace, {}).get("last_update")
        except Exception as err:
            _LOGGER.error("Error cargando viajes: %s", err)
            self._trips = {}
            self._recurring_trips = {}
            self._punctual_trips = {}
            self._last_update = None

    async def async_save_trips(self) -> None:
        """Guarda los viajes en el almacenamiento persistente."""
        try:
            # FIX: Usar namespace con entry_id para almacenamiento seguro
            namespace = f"{DOMAIN}_{self.hass.config_entries.async_get_entry(self.vehicle_id).entry_id}"
            self.hass.data.setdefault(namespace, {})["trips"] = self._trips
            self.hass.data[namespace]["recurring_trips"] = self._recurring_trips
            self.hass.data[namespace]["punctual_trips"] = self._punctual_trips
            self.hass.data[namespace]["last_update"] = datetime.now()
        except Exception as err:
            _LOGGER.error("Error guardando viajes: %s", err)

    async def async_get_recurring_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes recurrentes."""
        return list(self._recurring_trips.values())

    async def async_get_punctual_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes puntuales."""
        return list(self._punctual_trips.values())

    async def async_add_recurring_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje recurrente."""
        trip_id = kwargs.get("trip_id", str(len(self._recurring_trips) + 1))
        self._recurring_trips[trip_id] = {
            "id": trip_id,
            "dia_semana": kwargs["dia_semana"],
            "hora": kwargs["hora"],
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "activo": True,
        }
        await self.async_save_trips()

    async def async_add_punctual_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje puntual."""
        trip_id = kwargs.get("trip_id", str(len(self._punctual_trips) + 1))
        self._punctual_trips[trip_id] = {
            "id": trip_id,
            "datetime": kwargs["datetime"],
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "estado": "pendiente",
        }
        await self.async_save_trips()

    async def async_update_trip(self, trip_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza un viaje existente."""
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id].update(updates)
        elif trip_id in self._punctual_trips:
            self._punctual_trips[trip_id].update(updates)
        await self.async_save_trips()

    async def async_delete_trip(self, trip_id: str) -> None:
        """Elimina un viaje existente."""
        if trip_id in self._recurring_trips:
            del self._recurring_trips[trip_id]
        elif trip_id in self._punctual_trips:
            del self._punctual_trips[trip_id]
        await self.async_save_trips()

    async def async_pause_recurring_trip(self, trip_id: str) -> None:
        """Pausa un viaje recurrente."""
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id]["activo"] = False
        await self.async_save_trips()

    async def async_resume_recurring_trip(self, trip_id: str) -> None:
        """Reanuda un viaje recurrente."""
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id]["activo"] = True
        await self.async_save_trips()

    async def async_complete_punctual_trip(self, trip_id: str) -> None:
        """Marca un viaje puntual como completado."""
        if trip_id in self._punctual_trips:
            self._punctual_trips[trip_id]["estado"] = "completado"
        await self.async_save_trips()

    async def async_cancel_punctual_trip(self, trip_id: str) -> None:
        """Cancela un viaje puntual."""
        if trip_id in self._punctual_trips:
            del self._punctual_trips[trip_id]
        await self.async_save_trips()

    async def async_get_kwh_needed_today(self) -> float:
        """Calcula la energía necesaria para hoy basado en los viajes."""
        today = datetime.now().date()
        total_kwh = 0.0
        for trip in self._recurring_trips.values():
            if trip["activo"] and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        for trip in self._punctual_trips.values():
            if trip["estado"] == "pendiente" and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        return total_kwh

    async def async_get_hours_needed_today(self) -> int:
        """Calcula las horas necesarias para cargar hoy."""
        kwh_needed = await self.async_get_kwh_needed_today()
        charging_power = self.vehicle_controller.get_charging_power()
        return int(kwh_needed / charging_power) if charging_power > 0 else 0

    async def async_get_next_trip(self) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje programado."""
        now = datetime.now()
        next_trip = None
        for trip in self._recurring_trips.values():
            if trip["activo"]:
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        for trip in self._punctual_trips.values():
            if trip["estado"] == "pendiente":
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        return next_trip["trip"] if next_trip else None

    def _is_trip_today(self, trip: Dict[str, Any], today: datetime.date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        if trip["tipo"] == TRIP_TYPE_RECURRING:
            return today.strftime("%A").lower() == trip["dia_semana"]
        elif trip["tipo"] == TRIP_TYPE_PUNCTUAL:
            return datetime.strptime(trip["datetime"], "%Y-%m-%dT%H:%M").date() == today
        return False

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        if trip["tipo"] == TRIP_TYPE_RECURRING:
            now = datetime.now()
            today = now.date()
            day_of_week = now.weekday()
            target_day = self._get_day_index(trip["dia_semana"])
            days_ahead = (target_day - day_of_week) % 7
            if days_ahead == 0 and now.hour > int(trip["hora"].split(":")[0]):
                days_ahead = 7
            return datetime.combine(
                today + timedelta(days=days_ahead),
                datetime.strptime(trip["hora"], "%H:%M").time(),
            )
        elif trip["tipo"] == TRIP_TYPE_PUNCTUAL:
            return datetime.strptime(trip["datetime"], "%Y-%m-%dT%H:%M")
        return None

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana."""
        days = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        return days.index(day_name.lower())
