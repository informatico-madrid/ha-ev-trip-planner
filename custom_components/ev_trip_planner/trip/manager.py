"""Gestión central de viajes y optimización de carga para vehículos eléctricos.

Implementa la lógica de planificación de viajes, cálculo de energía necesaria
y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
runtime_data y tipado estricto.
"""

from __future__ import annotations

import datetime as _datetime_mod  # noqa: F401 — module-level for test mocking
import logging
from datetime import date, datetime, timezone
from pathlib import Path  # noqa: F401 — module-level for test mocking
from typing import Any, Dict, Optional


from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ._crud_mixin import _CRUDMixin
from ._power_profile_mixin import _PowerProfileMixin
from ._schedule_mixin import _ScheduleMixin
from ._sensor_callbacks import _SensorCallbacks
from ._soc_mixin import _SOCMixin

from ..emhass import EMHASSAdapter
from ..yaml_trip_storage import YamlTripStorage
from ..utils import is_trip_today as pure_is_trip_today
from ..utils import sanitize_recurring_trips as pure_sanitize_recurring_trips
from ..utils import validate_hora as pure_validate_hora

# T3.2: Import function for recurring trip rotation
from ..vehicle_controller import VehicleController

_UNSET = object()

_LOGGER = logging.getLogger(__name__)

# Instance counter for debugging
_trip_manager_instance_count = 0

# Days of week in Spanish (lowercase)
DAYS_OF_WEEK = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


class TripManager(_CRUDMixin, _SOCMixin, _PowerProfileMixin, _ScheduleMixin):
    """Gestión central de viajes y optimización de carga para vehículos eléctricos.

    Esta clase implementa la lógica de planificación de viajes, cálculo de energía
    necesaria y sincronización con EMHASS. Cumple con las reglas de Home Assistant
    2026 para runtime_data y tipado estricto.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        entry_id: Optional[str] = None,
        presence_config: Optional[Dict[str, Any]] = None,
        storage: Optional[YamlTripStorage] = None,
        emhass_adapter: Optional[EMHASSAdapter] = None,
    ) -> None:
        """Inicializa el gestor de viajes para un vehículo específico."""
        global _trip_manager_instance_count
        _trip_manager_instance_count += 1
        self._instance_id = _trip_manager_instance_count
        _CRUDMixin.__init__(self)
        _SOCMixin.__init__(self)
        _PowerProfileMixin.__init__(self)
        _ScheduleMixin.__init__(self)
        _LOGGER.debug(
            "=== TripManager instance created: id=%d, vehicle=%s ===",
            self._instance_id,
            vehicle_id,
        )

        self.hass = hass
        self.vehicle_id = vehicle_id
        self._entry_id: str = entry_id or ""
        self.vehicle_controller = VehicleController(
            hass, vehicle_id, presence_config, self
        )
        self._trips: Dict[str, Any] = {}
        self._recurring_trips: Dict[str, Any] = {}
        self._punctual_trips: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._storage: Optional[YamlTripStorage] = storage
        self._emhass_adapter: Optional[EMHASSAdapter] = emhass_adapter
        self._sensor_callbacks = _SensorCallbacks()

    def set_emhass_adapter(self, adapter: EMHASSAdapter) -> None:
        """Set the EMHASS adapter for this trip manager."""
        self._emhass_adapter = adapter
        _LOGGER.debug("EMHASS adapter set for vehicle %s", self.vehicle_id)

    def get_emhass_adapter(self) -> Optional[EMHASSAdapter]:
        """Get the EMHASS adapter for this trip manager."""
        return self._emhass_adapter

    def get_charging_power(self) -> float:
        """Get the configured charging power for the vehicle."""
        return self._get_charging_power()

    @staticmethod
    def _validate_hora(hora: str) -> None:
        """Valida que una cadena de hora tenga el formato HH:MM y valores válidos.

        Delegates to pure utils.validate_hora for testability.

        Args:
            hora: Cadena de hora en formato HH:MM.

        Raises:
            ValueError: Si el formato no es HH:MM o los valores están fuera de rango.
        """
        pure_validate_hora(hora)

    def _sanitize_recurring_trips(self, trips: Dict[str, Any]) -> Dict[str, Any]:
        """Elimina viajes recurrentes con formato de hora inválido del almacenamiento."""
        original_count = len(trips)
        sanitized = pure_sanitize_recurring_trips(trips)
        removed_count = original_count - len(sanitized)
        if removed_count > 0:
            _LOGGER.warning(
                "%d recurring trip(s) ignored due to invalid hora format. "
                "Fix or remove invalid entries from storage.",
                removed_count,
            )
        return sanitized

    def _parse_trip_datetime(
        self, trip_datetime: datetime | str, allow_none: bool = False
    ) -> datetime | None:
        """Parse trip datetime, ensuring timezone awareness for both object and string inputs."""
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
                if allow_none:
                    return None
                return datetime.now(timezone.utc)
            return parsed
        except Exception:
            _LOGGER.warning(
                "Failed to parse trip datetime: %s", repr(trip_datetime)
            )
            return None if allow_none else datetime.now(timezone.utc)

    def _is_trip_today(self, trip: Dict[str, Any], today: date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        return pure_is_trip_today(trip, today)

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        from ..calculations import calculate_trip_time

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
        """Obtiene el índice del día de la semana (0=lunes, 6=domingo)."""
        try:
            idx = DAYS_OF_WEEK.index(day_name.lower())
            return idx
        except ValueError:
            _LOGGER.warning("Unknown day name: %s, defaulting to 0", day_name)
            return 0

    async def async_get_next_trip_after(
        self, hora_regreso: datetime
    ) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje pendiente después de una hora de regreso.

        Filters punctual trips with datetime > hora_regreso and estado=pendiente,
        and recurring trips with hora > hora_regreso.time() for today's day of week
        and activo=True.
        """
        next_trip: Optional[Dict[str, Any]] = None
        hoy = hora_regreso.date()
        dia_semana_hoy = DAYS_OF_WEEK[hoy.weekday()]

        # Filter punctual trips: datetime > hora_regreso and estado=pendiente
        for trip in self._punctual_trips.values():
            if trip.get("estado") != "pendiente":
                continue
            trip_time = self._get_trip_time(trip)
            if trip_time and trip_time > hora_regreso:
                if next_trip is None or trip_time < next_trip["time"]:
                    next_trip = {"time": trip_time, "trip": trip}

        # Filter recurring trips: today's day_of_week, hora > hora_regreso.time(), activo=True
        for trip in self._recurring_trips.values():
            if not trip.get("activo", True):
                continue
            if trip.get("dia_semana", "").lower() != dia_semana_hoy:
                continue
            try:
                trip_hour = int(trip["hora"].split(":")[0])
                trip_minute = int(trip["hora"].split(":")[1])
                regreso_hour = hora_regreso.hour
                regreso_minute = hora_regreso.minute
                if trip_hour < regreso_hour or (
                    trip_hour == regreso_hour and trip_minute <= regreso_minute
                ):
                    continue
                trip_time = datetime.combine(
                    hoy, datetime.strptime(trip["hora"], "%H:%M").time()
                )
            except (ValueError, KeyError) as err:
                _LOGGER.warning(
                    "Invalid trip hora format: %s — skipping. Error: %s",
                    trip.get("hora"),
                    err,
                )
                continue
            if next_trip is None or trip_time < next_trip["time"]:
                next_trip = {"time": trip_time, "trip": trip}

        return next_trip["trip"] if next_trip else None

    async def async_get_next_trip(self) -> Optional[Dict[str, Any]]:
        """Get the next scheduled trip from all trips."""
        now = datetime.now(timezone.utc)
        next_trip: Optional[Dict[str, Any]] = None
        for trip in self._recurring_trips.values():
            if trip.get("activo"):
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        return next_trip["trip"] if next_trip else None

