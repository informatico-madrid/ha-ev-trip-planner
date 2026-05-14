"""Trip navigation — next-trip lookup.

Migrated from manager.py:272-340. Plain class (no inheritance).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)

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


class TripNavigator:
    """Next-trip lookup for TripManager."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # CC-N-ACCEPTED: cc=11 — trip type dispatch (punctual vs recurring),
    # state checks (pending, active), day-of-week matching, time parsing
    # with error recovery, and nearest-trip selection. Each branch is a
    # distinct domain rule; the branching IS the business logic.
    async def async_get_next_trip_after(
        self, hora_regreso: datetime
    ) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje pendiente después de una hora de regreso."""
        next_trip: Optional[Dict[str, Any]] = None
        hoy = hora_regreso.date()
        dia_semana_hoy = DAYS_OF_WEEK[hoy.weekday()]

        # Filter punctual trips: datetime > hora_regreso and estado=pendiente
        for trip in self._state.punctual_trips.values():
            if trip.get("estado") != "pendiente":
                continue
            trip_time = self._state._soc._get_trip_time(trip)
            if trip_time and trip_time > hora_regreso:
                if next_trip is None or trip_time < next_trip["time"]:
                    next_trip = {"time": trip_time, "trip": trip}

        # Filter recurring trips: today's day_of_week, hora > hora_regreso.time(), activo=True
        for trip in self._state.recurring_trips.values():
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

    # CC-N-ACCEPTED: cc=11 — trip type dispatch (recurring vs punctual),
    # state checks (active, pending), time validity, and nearest-trip
    # selection. Same pattern as async_get_next_trip_after; each branch
    # is a distinct domain rule with no natural grouping to reduce cc.
    async def async_get_next_trip(self) -> Optional[Dict[str, Any]]:
        """Get the next scheduled trip from all trips."""
        now = datetime.now(timezone.utc)
        next_trip: Optional[Dict[str, Any]] = None
        for trip in self._state.recurring_trips.values():
            if trip.get("activo"):
                trip_time = self._state._soc._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        for trip in self._state.punctual_trips.values():
            if trip.get("estado") == "pendiente":
                trip_time = self._state._soc._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        return next_trip["trip"] if next_trip else None
