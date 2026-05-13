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
    calculate_charging_rate,
    calculate_day_index,
    calculate_soc_target,
    calculate_trip_time,
    compute_safe_delta,
)
from ..const import CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER, DOMAIN
from ..utils import calcular_energia_kwh
from ..utils import is_trip_today as pure_is_trip_today
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
        """Calcula la energía necesaria considerando el SOC actual."""
        battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
        charging_power_kw = vehicle_config.get("charging_power_kw", 3.6)
        soc_current = vehicle_config.get("soc_current", 100.0)
        consumption_kwh_per_km = vehicle_config.get("consumption_kwh_per_km", 0.15)
        safety_margin_percent = vehicle_config.get("safety_margin_percent", 10.0)

        if "kwh" in trip:
            energia_viaje = trip.get("kwh", 0.0)
        else:
            distance_km = trip.get("km", 0.0)
            energia_viaje = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

        energia_actual = (soc_current / 100.0) * battery_capacity
        energia_necesaria = max(0.0, energia_viaje - energia_actual)
        energia_final = energia_necesaria * (1 + safety_margin_percent / 100)
        horas_carga = (
            energia_final / charging_power_kw if charging_power_kw > 0 else 0.0
        )

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
            alerta_tiempo_insuficiente = horas_carga > horas_disponibles

        return {
            "energia_necesaria_kwh": round(energia_final, 3),
            "horas_carga_necesarias": round(horas_carga, 2),
            "alerta_tiempo_insuficiente": alerta_tiempo_insuficiente,
            "horas_disponibles": round(horas_disponibles, 2),
            "margen_seguridad_aplicado": safety_margin_percent,
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

    # ── Private helpers (previously on SOCHelpers) ────────────────

    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> datetime | None:
        """Parse trip datetime, ensuring timezone awareness."""
        if isinstance(trip_datetime, datetime):
            dt = trip_datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        from homeassistant.util import dt as dt_util

        try:
            parsed = dt_util.parse_datetime(trip_datetime)
            if parsed is not None and parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed is None:
                _LOGGER.warning(
                    "Failed to parse trip datetime: %s, falling back to now",
                    repr(trip_datetime),
                )
                return None if allow_none else datetime.now(timezone.utc)
            return parsed
        except Exception:
            _LOGGER.warning("Failed to parse trip datetime: %s", repr(trip_datetime))
            return None if allow_none else datetime.now(timezone.utc)

    @staticmethod
    def _compute_charging_hours(trip_time: datetime, now: datetime) -> float:
        """Compute available charging hours from a trip datetime.

        Uses timezone-safe delta computation. Returns 0.0 if delta cannot be computed.
        """
        delta = compute_safe_delta(trip_time, now)
        if delta is None:
            return 0.0
        return max(0.0, delta.total_seconds() / 3600)

    def _get_charging_power(self) -> float:
        """Obtiene la potencia de carga desde la configuración."""
        try:
            entry: Optional[ConfigEntry] = None
            for config_entry in self._state.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("vehicle_name") == self._state.vehicle_id:
                    entry = config_entry
                    break
            if entry is not None and entry.data is not None:
                power = entry.data.get(CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER)
                if isinstance(power, (int, float)) and power > 0:
                    return float(power)
        except Exception:
            pass
        return DEFAULT_CHARGING_POWER

    def _calcular_tasa_carga_soc(
        self, charging_power_kw: float, battery_capacity_kwh: float = 50.0
    ) -> float:
        """Calcula la tasa de carga en % SOC/hora."""
        return calculate_charging_rate(charging_power_kw, battery_capacity_kwh)

    def _calcular_soc_objetivo_base(
        self,
        trip: Dict[str, Any],
        battery_capacity_kwh: float,
        consumption_kwh_per_km: float = 0.15,
    ) -> float:
        """Calculates the base SOC target percentage for a trip."""
        return calculate_soc_target(trip, battery_capacity_kwh, consumption_kwh_per_km)

    def _is_trip_today(self, trip: Dict[str, Any], today: date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        return pure_is_trip_today(trip, today)

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        tipo = trip.get("tipo")
        if tipo is None:
            return None
        result = calculate_trip_time(
            tipo,
            trip.get("hora"),
            trip.get("dia_semana"),
            trip.get("datetime"),
            datetime.now(timezone.utc),
        )
        if result is not None:
            return result.replace(tzinfo=timezone.utc)
        return result

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana."""
        return calculate_day_index(day_name)
