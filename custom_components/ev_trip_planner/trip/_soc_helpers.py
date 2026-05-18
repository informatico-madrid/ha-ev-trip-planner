"""SOC helpers — private utilities for SOC calculations.

Migrated from _soc_helpers_mixin.py. Plain class (no inheritance).
All methods are private (prefixed with _).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from ..calculations import (
    calculate_charging_rate,
    calculate_day_index,
    calculate_soc_target,
    calculate_trip_time,
)
from ..const import CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER, DOMAIN
from ..utils import is_trip_today as pure_is_trip_today
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class SOCHelpers:
    """Stateless SOC helpers shared by SOC calculations.

    All methods are private (prefixed with _) — no SOLID public-method count.
    """

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> datetime | None:
        """Parse trip datetime, ensuring timezone awareness."""
        if isinstance(trip_datetime, datetime):
            dt = trip_datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
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

    def _get_charging_power(self) -> float:
        """Obtiene la potencia de carga desde la configuración."""
        try:
            entry: Optional[ConfigEntry[Any]] = None
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
