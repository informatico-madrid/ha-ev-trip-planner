"""SOC query mixin — SOC fetching and energy calculation.

Migrated from _soc_query_mixin.py. Plain class (no inheritance).
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from ..calculations import (
    calculate_energy_needed,
    compute_safe_delta,
)
from ..const import DOMAIN
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class SOCQuery:
    """SOC fetching and energy calculation."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    async def async_get_vehicle_soc(self, vehicle_id: str) -> float:
        """Fetch current SOC from the configured HA sensor."""
        try:
            entry: Optional[ConfigEntry[Any]] = None
            for config_entry in self._state.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("vehicle_name") == vehicle_id:
                    entry = config_entry
                    break
            if entry and entry.data:
                soc_sensor = entry.data.get("soc_sensor")
                if soc_sensor:
                    state = self._state.hass.states.get(soc_sensor)
                    if state and state.state not in ("unknown", "unavailable", "none"):
                        return float(state.state)
                _LOGGER.warning("Sensor SOC no disponible para %s", vehicle_id)
            else:
                _LOGGER.warning("Config entry no encontrada para %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Error obteniendo SOC: %s", err)
        return 0.0

    async def async_calcular_energia_necesaria(
        self, trip: Dict[str, Any], vehicle_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula la energía necesaria considerando el SOC actual.

        Delegates to calculate_energy_needed (windows.py) for the pure energy
        calculation with proper safety margin — no silent defaults here.
        Only adds the time-check logic (horas_disponibles, alerta).
        """
        # Validate required fields — no silent defaults
        for field in ("battery_capacity_kwh", "charging_power_kw"):
            if field not in vehicle_config:
                _LOGGER.error(
                    "async_calcular_energia_necesaria: missing required field '%s' "
                    "in vehicle_config for trip %s",
                    field,
                    trip.get("id"),
                )
                return {
                    "energia_necesaria_kwh": 0.0,
                    "horas_carga_necesarias": 0,
                    "alerta_tiempo_insuficiente": True,
                    "horas_disponibles": 0.0,
                    "margen_seguridad_aplicado": 0.0,
                }

        # Pure energy calculation — no time check, delegates to canonical impl
        # vehicle_config always has battery_capacity_kwh, charging_power_kw, safety_margin_percent
        # consumption_kwh_per_km comes from config flow (default 0.15)
        energia_info = calculate_energy_needed(
            trip=trip,
            battery_capacity_kwh=vehicle_config["battery_capacity_kwh"],
            soc_current=vehicle_config["soc_current"],
            charging_power_kw=vehicle_config["charging_power_kw"],
            consumption_kwh_per_km=vehicle_config.get("consumption_kwh_per_km", 0.15),
            safety_margin_percent=vehicle_config["safety_margin_percent"],
        )

        # Time-check logic (only applies when trip has a datetime)
        horas_disponibles = 0.0
        alerta_tiempo_insuficiente = False
        trip_tipo = trip.get("tipo")
        trip_datetime = trip.get("datetime")
        trip_time: Optional[datetime] = None

        if trip_datetime:
            try:
                trip_time = (
                    self._state._soc._get_trip_time(trip)
                    if trip_tipo
                    else self._state._soc._parse_trip_datetime(trip_datetime)
                )
            except (KeyError, ValueError, TypeError):
                trip_time = None

        if trip_time:
            now = dt_util.now() if trip_tipo else datetime.now(timezone.utc)
            horas_disponibles = self._compute_charging_hours(trip_time, now)
            # Use horas from energy calc (rounded up) for consistency
            horas_carga = energia_info["horas_carga_necesarias"]
            alerta_tiempo_insuficiente = horas_carga > horas_disponibles

        return {
            "energia_necesaria_kwh": energia_info["energia_necesaria_kwh"],
            "horas_carga_necesarias": energia_info["horas_carga_necesarias"],
            "alerta_tiempo_insuficiente": alerta_tiempo_insuficiente,
            "horas_disponibles": round(horas_disponibles, 2),
            "margen_seguridad_aplicado": energia_info["margen_seguridad_aplicado"],
        }

    async def async_get_kwh_needed_today(self) -> float:
        """Calcula la energía necesaria para hoy basado en los viajes."""
        today = datetime.now(timezone.utc).date()
        total_kwh = 0.0
        for trip in self._state.recurring_trips.values():
            if trip["activo"] and self._state._soc._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        for trip in self._state.punctual_trips.values():
            if trip["estado"] == "pendiente" and self._state._soc._is_trip_today(
                trip, today
            ):
                total_kwh += trip["kwh"]
        return total_kwh

    async def async_get_hours_needed_today(self) -> int:
        """Calcula las horas necesarias para cargar hoy."""
        kwh_needed = await self.async_get_kwh_needed_today()
        charging_power = self._get_charging_power()
        return math.ceil(kwh_needed / charging_power) if charging_power > 0 else 0

    # ── Private helpers (delegated to SOCHelpers via state) ─────────

    @staticmethod
    def _compute_charging_hours(trip_time: datetime, now: datetime) -> float:
        """Compute available charging hours from a trip datetime.

        Uses timezone-safe delta computation. Returns 0.0 if delta cannot be computed.
        """
        delta = compute_safe_delta(trip_time, now)
        if delta is None:
            return 0.0
        return max(0.0, delta.total_seconds() / 3600)

    # Delegate to SOCHelpers — shared logic lives in one place
    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> datetime | None:
        """Parse trip datetime, ensuring timezone awareness."""
        return self._state._soc_helpers._parse_trip_datetime(trip_datetime, allow_none)

    def _get_charging_power(self) -> float:
        """Obtiene la potencia de carga desde la configuración."""
        return self._state._soc_helpers._get_charging_power()

    def _calcular_tasa_carga_soc(
        self, charging_power_kw: float, battery_capacity_kwh: float = 50.0
    ) -> float:
        """Calcula la tasa de carga en % SOC/hora."""
        return self._state._soc_helpers._calcular_tasa_carga_soc(
            charging_power_kw, battery_capacity_kwh
        )

    def _calcular_soc_objetivo_base(
        self,
        trip: Dict[str, Any],
        battery_capacity_kwh: float,
        consumption_kwh_per_km: float = 0.15,
    ) -> float:
        """Calculates the base SOC target percentage for a trip.

        Delegates to SOCHelpers — implementation lives in one place (SOCHelpers).
        """
        return self._state._soc_helpers._calcular_soc_objetivo_base(
            trip, battery_capacity_kwh, consumption_kwh_per_km
        )

    def _is_trip_today(self, trip: Dict[str, Any], today: date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        return self._state._soc_helpers._is_trip_today(trip, today)

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        return self._state._soc_helpers._get_trip_time(trip)

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana."""
        return self._state._soc_helpers._get_day_index(day_name)
